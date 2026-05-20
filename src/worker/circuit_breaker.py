# src/worker/circuit_breaker.py
"""
Generalized Circuit Breaker

Provides per-task-type circuit breaker isolation. Each ``type_id`` gets its own
``pybreaker.CircuitBreaker`` instance so that failures in one task type do not
affect others.
"""

import os
import random
from typing import Dict

import pybreaker

from config import settings


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
