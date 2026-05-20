# src/worker/circuit_breaker.py
"""
Generalized Circuit Breaker

Provides per-task-type circuit breaker isolation. Each ``type_id`` gets its own
``pybreaker.CircuitBreaker`` instance so that failures in one task type do not
affect others.
"""

import asyncio
import os
import random
from typing import Dict, List

import httpx
import pybreaker

from config import settings
from rate_limiter import wait_for_rate_limit_token


# ---------------------------------------------------------------------------
# Per-type circuit breaker factory
# ---------------------------------------------------------------------------

_circuit_breakers: Dict[str, pybreaker.CircuitBreaker] = {}


def get_circuit_breaker(type_id: str) -> pybreaker.CircuitBreaker:
    """
    Return (and lazily create) a per-``type_id`` circuit breaker.

    Args:
        type_id: The task type identifier (e.g. "summarize", "translate")

    Returns:
        A ``pybreaker.CircuitBreaker`` instance dedicated to *type_id*
    """
    if type_id not in _circuit_breakers:
        _circuit_breakers[type_id] = pybreaker.CircuitBreaker(
            fail_max=settings.circuit_breaker_fail_max,
            reset_timeout=settings.circuit_breaker_reset_timeout,
            exclude=[KeyboardInterrupt],
        )
    return _circuit_breakers[type_id]


# ---------------------------------------------------------------------------
# Helpers (unchanged / generic)
# ---------------------------------------------------------------------------


def calculate_backoff_delay(
    attempt: int, base_delay: float = 1.0, max_delay: float = 300.0
) -> float:
    """
    Calculate exponential backoff delay with jitter for rate limiting.

    Args:
        attempt: The retry attempt number (0-based)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds

    Returns:
        Delay in seconds with jitter applied
    """
    # Exponential backoff: base_delay * (2 ^ attempt)
    delay = base_delay * (2**attempt)

    # Cap at max_delay
    delay = min(delay, max_delay)

    # Add jitter (+-25% of the delay)
    jitter = delay * 0.25 * (2 * random.random() - 1)
    final_delay = delay + jitter

    # Ensure minimum delay of base_delay
    return max(final_delay, base_delay)


def get_container_id() -> str:
    """Get Docker container ID from /proc/self/cgroup or hostname."""
    try:
        # Try to get container ID from cgroup (most reliable method)
        with open("/proc/self/cgroup", "r") as f:
            for line in f:
                if "docker" in line:
                    # Extract container ID from cgroup path
                    parts = line.strip().split("/")
                    for part in reversed(parts):
                        if (
                            len(part) == 64 and part.isalnum()
                        ):  # Docker container ID format
                            return part[:12]  # Return short container ID
                        elif part.startswith("docker-") and part.endswith(".scope"):
                            # systemd format: docker-<container_id>.scope
                            container_id = part[
                                7:-6
                            ]  # Remove 'docker-' prefix and '.scope' suffix
                            return container_id[:12]

        # Fallback: use hostname (often set to container ID in Docker)
        hostname = os.uname().nodename
        if len(hostname) >= 12:
            return hostname[:12]

        return hostname

    except Exception:
        # Final fallback: use hostname or unknown
        try:
            return os.uname().nodename[:12]
        except Exception:
            return "unknown"


# ---------------------------------------------------------------------------
# Generic API caller with per-type circuit breaker
# ---------------------------------------------------------------------------


async def call_api(
    type_id: str,
    messages: List[Dict[str, str]],
    retry_attempt: int = 0,
) -> str:
    """
    Call an API with circuit breaker protection and distributed rate limiting.

    The circuit breaker used is determined by *type_id*, providing full
    isolation between different task types.

    Args:
        type_id: The task type identifier
        messages: List of message dictionaries for the chat completion API
                 (e.g., [{"role": "user", "content": "..."}])
        retry_attempt: Current retry attempt number for backoff calculation

    Returns:
        The response content from the API

    Raises:
        Exception: If the API call fails
    """
    breaker = get_circuit_breaker(type_id)

    # Use the circuit breaker as a decorator-style context via __call__
    # We wrap the inner coroutine so each type_id uses its own breaker.
    @breaker
    async def _inner_call() -> str:
        # Acquire a rate limit token from the distributed rate limiter
        rate_limit_timeout = 60.0

        if not await wait_for_rate_limit_token(
            type_id, tokens=1, timeout=rate_limit_timeout
        ):
            raise Exception(
                f"Rate limit token acquisition timeout after {rate_limit_timeout}s "
                f"for type '{type_id}'"
            )

        max_retries = 5

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{settings.openrouter_base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {settings.openrouter_api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": settings.openrouter_model,
                            "messages": messages,
                        },
                        timeout=settings.openrouter_timeout,
                    )

                    # Handle rate limiting (HTTP 429) with exponential backoff
                    if response.status_code == 429:
                        if attempt < max_retries - 1:
                            # Check for Retry-After header
                            retry_after = response.headers.get("retry-after")
                            if retry_after:
                                try:
                                    delay = float(retry_after)
                                except ValueError:
                                    delay = calculate_backoff_delay(
                                        attempt, base_delay=60.0
                                    )
                            else:
                                delay = calculate_backoff_delay(
                                    attempt, base_delay=60.0
                                )

                            # Add extra jitter for thundering herd prevention
                            jitter = random.uniform(0, min(delay * 0.1, 30))
                            total_delay = delay + jitter

                            await asyncio.sleep(total_delay)
                            continue
                        else:
                            raise Exception(
                                f"API rate limit exceeded after {max_retries} "
                                f"attempts for type '{type_id}': "
                                f"{response.status_code}"
                            )

                    # Handle other HTTP errors
                    if response.status_code != 200:
                        raise Exception(
                            f"API error for type '{type_id}': "
                            f"{response.status_code}"
                        )

                    result = response.json()
                    return result["choices"][0]["message"]["content"]

            except httpx.TimeoutException:
                if attempt < max_retries - 1:
                    delay = calculate_backoff_delay(
                        attempt, base_delay=2.0, max_delay=60.0
                    )
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise Exception(
                        f"API timeout after multiple attempts for type '{type_id}'"
                    )
            except httpx.RequestError as e:
                if attempt < max_retries - 1:
                    delay = calculate_backoff_delay(
                        attempt, base_delay=1.0, max_delay=30.0
                    )
                    await asyncio.sleep(delay)
                    continue
                else:
                    raise Exception(
                        f"API request error for type '{type_id}': {str(e)}"
                    )

        # All attempts exhausted
        raise Exception(
            f"API call failed after all retry attempts for type '{type_id}'"
        )

    return await _inner_call()


# ---------------------------------------------------------------------------
# Status / admin helpers (now type-aware)
# ---------------------------------------------------------------------------


def get_circuit_breaker_status(type_id: str) -> dict:
    """
    Get current circuit breaker status for a specific task type.

    Args:
        type_id: The task type identifier

    Returns:
        Dictionary with circuit breaker state information
    """
    try:
        breaker = get_circuit_breaker(type_id)
        status = {
            "type_id": type_id,
            "state": breaker.current_state,
            "fail_count": getattr(breaker, "fail_counter", 0),
            "success_count": getattr(breaker, "success_counter", 0),
            "container_id": get_container_id(),
        }

        if hasattr(breaker, "last_failure_time"):
            status["last_failure_time"] = breaker.last_failure_time

        if hasattr(breaker, "_last_failure"):
            status["last_failure"] = str(breaker._last_failure)

        return status

    except Exception as e:
        return {
            "type_id": type_id,
            "state": "error",
            "error": str(e),
            "container_id": get_container_id(),
        }


def reset_circuit_breaker(type_id: str) -> bool:
    """
    Manually reset the circuit breaker for a specific task type.

    Args:
        type_id: The task type identifier

    Returns:
        True on success
    """
    breaker = get_circuit_breaker(type_id)
    try:
        if hasattr(breaker, "reset"):
            breaker.reset()
        elif hasattr(breaker, "_reset"):
            breaker._reset()
        else:
            if hasattr(breaker, "_failure_count"):
                breaker._failure_count = 0
            if hasattr(breaker, "_state_storage"):
                breaker._state_storage.state = "closed"
            elif hasattr(breaker, "_state"):
                breaker._state = "closed"
        return True
    except Exception as e:
        raise Exception(
            f"Failed to reset circuit breaker for type '{type_id}': {str(e)}"
        )


def open_circuit_breaker(type_id: str) -> bool:
    """
    Manually open the circuit breaker for a specific task type.

    Args:
        type_id: The task type identifier

    Returns:
        True on success
    """
    breaker = get_circuit_breaker(type_id)
    try:
        if hasattr(breaker, "_failure_count"):
            breaker._failure_count = breaker.fail_max + 1

        try:
            breaker._on_failure()
        except Exception:
            if hasattr(breaker, "_state_storage"):
                breaker._state_storage.state = "open"
            elif hasattr(breaker, "_state"):
                breaker._state = "open"

        return True
    except Exception as e:
        raise Exception(
            f"Failed to open circuit breaker for type '{type_id}': {str(e)}"
        )
