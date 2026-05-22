# src/worker/tasks.py
"""
Celery tasks for generalized task processing.

This module processes tasks using the GenericAPIExecutor, which makes HTTP API
calls based on task type configurations stored in Redis. Each task type defines
its own endpoint, authentication, request template, and response parsing.
"""

import asyncio
import json
import os
import random
import time
from datetime import UTC, datetime
from typing import Optional

import redis.asyncio as aioredis
from celery import Celery, Task
from celery.worker.control import Panel

from api_executor import GenericAPIExecutor, PermanentError, TransientError, DependencyError, ExecutionResult
from config import settings
from rate_limiter import wait_for_rate_limit_token

# --- Constants ------------------------------------------------------------

DEFAULT_RETRY_SCHEDULE = [5, 15, 60, 300]

# --- Celery App Setup -----------------------------------------------------

app = Celery(
    "asynctaskflow-worker",
    broker=settings.celery_broker_url,
    backend=None,  # Disable result backend - we use custom task:{task_id} storage
)

# Configure Celery
app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Worker settings
    worker_concurrency=settings.worker_concurrency,
    worker_prefetch_multiplier=settings.worker_prefetch_multiplier,
    task_soft_time_limit=settings.task_soft_time_limit,
    task_time_limit=settings.task_time_limit,
    # Disable result backend completely
    task_ignore_result=True,
    # Task routing
    task_routes={
        "process_task": {"queue": "celery"},
        "process_scheduled_tasks": {"queue": "celery"},
    },
)

# --- Remote-Control Health Commands --------------------------------------


@Panel.register
def get_worker_health(panel, **kwargs):
    """Return health info for this worker (invoked via broadcast)."""
    type_id = kwargs.get("type_id", "default")
    try:
        from circuit_breaker import get_circuit_breaker_status
        cb_status = get_circuit_breaker_status(type_id)
    except Exception:
        cb_status = {"state": "unknown", "error": "Failed to get status"}

    return {
        "worker_id": f"worker-{os.getpid()}",
        "type_id": type_id,
        "circuit_breaker": cb_status,
        "status": "healthy" if cb_status.get("state") != "open" else "unhealthy",
        "timestamp": time.time(),
    }


@Panel.register
def reset_worker_circuit_breaker(panel, **kwargs):
    """Reset the circuit breaker on this worker (invoked via broadcast)."""
    type_id = kwargs.get("type_id", "default")
    try:
        from circuit_breaker import reset_circuit_breaker, get_circuit_breaker_status
        reset_circuit_breaker(type_id)
        return {
            "status": "success",
            "message": f"Circuit breaker reset for type '{type_id}'.",
            "new_state": get_circuit_breaker_status(type_id),
            "worker_id": f"worker-{os.getpid()}",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "worker_id": f"worker-{os.getpid()}",
        }


@Panel.register
def open_worker_circuit_breaker(panel, **kwargs):
    """Open the circuit breaker on this worker (invoked via broadcast)."""
    type_id = kwargs.get("type_id", "default")
    try:
        from circuit_breaker import open_circuit_breaker, get_circuit_breaker_status
        open_circuit_breaker(type_id)
        return {
            "status": "success",
            "message": f"Circuit breaker opened for type '{type_id}'.",
            "new_state": get_circuit_breaker_status(type_id),
            "worker_id": f"worker-{os.getpid()}",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "worker_id": f"worker-{os.getpid()}",
        }


# --- Async Redis and State Management Helpers -----------------------------


async def get_async_redis_connection() -> aioredis.Redis:
    """Get an optimized async Redis connection."""
    try:
        from redis_config import get_worker_standard_redis
        return await get_worker_standard_redis()
    except RuntimeError:
        # Fallback to direct connection if worker Redis not initialized
        return aioredis.from_url(settings.redis_url, decode_responses=True)


def classify_error(status_code: int, error_message: str) -> str:
    """Classify error using the GenericAPIExecutor's classification logic."""
    executor = GenericAPIExecutor()
    if status_code and status_code >= 400:
        error_class = executor._classify_http_status(status_code)
    else:
        error_class = executor._classify_error_message(error_message)
    return error_class.__name__


def calculate_retry_delay(
    retry_count: int, error_type: str = "", schedule_str: Optional[str] = None
) -> float:
    """Calculate retry delay with exponential backoff and jitter.

    Uses the per-type retry_schedule from config if provided,
    otherwise falls back to DEFAULT_RETRY_SCHEDULE.
    """
    if schedule_str and schedule_str.strip():
        schedule = [float(x.strip()) for x in schedule_str.split(",") if x.strip()]
    else:
        schedule = DEFAULT_RETRY_SCHEDULE
    base_delay = schedule[min(retry_count, len(schedule) - 1)]
    jitter = random.uniform(0, base_delay * 0.1)
    return base_delay + jitter


async def update_task_state(
    redis_conn: aioredis.Redis, task_id: str, state: str, **kwargs
) -> None:
    """Update task state and metadata in Redis asynchronously."""
    current_time = datetime.now(UTC).isoformat()
    fields = {"state": state, "updated_at": current_time}
    fields.update(kwargs)

    # Get current state for counter updates
    current_task_data = await redis_conn.hgetall(f"task:{task_id}")
    old_state = current_task_data.get("state") if current_task_data else None

    # Add state-specific timestamps
    if state == "ACTIVE":
        fields["started_at"] = current_time
    elif state == "COMPLETED":
        fields["completed_at"] = current_time
    elif state == "FAILED":
        fields["failed_at"] = current_time
    elif state == "DLQ":
        fields["dlq_at"] = current_time
    elif state == "SCHEDULED":
        fields["scheduled_at"] = current_time

    # Handle error history and retry timestamps
    if "last_error" in kwargs and kwargs["last_error"]:
        existing_data = await redis_conn.hgetall(f"task:{task_id}")

        # Handle error history
        error_history = []
        if existing_data.get("error_history"):
            try:
                error_history = json.loads(existing_data["error_history"])
            except (json.JSONDecodeError, TypeError):
                error_history = []

        error_entry = {
            "timestamp": current_time,
            "error": kwargs["last_error"],
            "error_type": kwargs.get("error_type", "Unknown"),
            "retry_count": kwargs.get("retry_count", 0),
            "state_transition": f"{existing_data.get('state', 'UNKNOWN')} -> {state}",
        }
        error_history.append(error_entry)
        fields["error_history"] = json.dumps(error_history)

        # Handle retry timestamps
        if state == "SCHEDULED":
            retry_timestamps = []
            if existing_data.get("retry_timestamps"):
                try:
                    retry_timestamps = json.loads(existing_data["retry_timestamps"])
                except (json.JSONDecodeError, TypeError):
                    retry_timestamps = []

            retry_entry = {
                "retry_number": kwargs.get("retry_count", 0),
                "scheduled_at": current_time,
                "retry_after": kwargs.get("retry_after"),
                "error_type": kwargs.get("error_type", "Unknown"),
                "delay_seconds": None,
            }
            retry_timestamps.append(retry_entry)
            fields["retry_timestamps"] = json.dumps(retry_timestamps)

    # Track when a retry actually starts
    if state == "ACTIVE":
        existing_data = await redis_conn.hgetall(f"task:{task_id}")
        if existing_data.get("retry_timestamps"):
            try:
                retry_timestamps = json.loads(existing_data["retry_timestamps"])
                if retry_timestamps:
                    latest_retry = retry_timestamps[-1]
                    if "actual_start_at" not in latest_retry:
                        latest_retry["actual_start_at"] = current_time
                        if latest_retry.get("scheduled_at"):
                            scheduled_time = datetime.fromisoformat(
                                latest_retry["scheduled_at"].replace("Z", "+00:00")
                            )
                            actual_time = datetime.fromisoformat(
                                current_time.replace("Z", "+00:00")
                            )
                            delay_seconds = (actual_time - scheduled_time).total_seconds()
                            latest_retry["delay_seconds"] = delay_seconds
                        fields["retry_timestamps"] = json.dumps(retry_timestamps)
            except (json.JSONDecodeError, TypeError, ValueError):
                pass

    # --- Fix #1: Append to state_history ---
    state_history = []
    if current_task_data.get("state_history"):
        try:
            state_history = json.loads(current_task_data["state_history"])
        except (json.JSONDecodeError, TypeError):
            state_history = []
    state_history.append({
        "from": old_state or "UNKNOWN",
        "to": state,
        "timestamp": current_time,
    })
    fields["state_history"] = json.dumps(state_history)

    # Serialize complex types
    for key, value in fields.items():
        if isinstance(value, (dict, list)) and key not in ("error_history", "state_history"):
            fields[key] = json.dumps(value)
        elif value is not None:
            fields[key] = str(value)

    # Update task data atomically
    async with redis_conn.pipeline(transaction=True) as pipe:
        await pipe.hset(f"task:{task_id}", mapping=fields)
        # Fix #5: Set TTL on completed/DLQ tasks (default 24 hours = 86400s)
        if state in ("COMPLETED", "DLQ"):
            task_ttl = int(os.environ.get("TASK_RESULT_TTL", "86400"))
            await pipe.expire(f"task:{task_id}", task_ttl)
        await pipe.execute()

    # Publish real-time update
    try:
        queue_depths = {}
        queue_depths["primary"] = await redis_conn.llen("tasks:pending:primary")
        queue_depths["retry"] = await redis_conn.llen("tasks:pending:retry")
        queue_depths["scheduled"] = await redis_conn.zcard("tasks:scheduled")
        queue_depths["dlq"] = await redis_conn.llen("dlq:tasks")

        update_data = {
            "type": "task_state_changed",
            "task_id": task_id,
            "old_state": old_state,
            "new_state": state,
            "queue_depths": queue_depths,
            "timestamp": current_time,
        }
        await redis_conn.publish("queue-updates", json.dumps(update_data))
    except Exception as e:
        print(f"Warning: Failed to publish queue update: {e}")


async def move_to_dlq(
    redis_conn: aioredis.Redis, task_id: str, reason: str, error_type: str = "Unknown"
) -> None:
    """Move a task to the dead-letter queue asynchronously."""
    await update_task_state(
        redis_conn,
        task_id,
        "DLQ",
        last_error=reason,
        error_type=error_type,
        completed_at=datetime.now(UTC).isoformat(),
    )
    await redis_conn.lpush("dlq:tasks", task_id)


async def schedule_task_for_retry(
    redis_conn: aioredis.Redis,
    task_id: str,
    retry_count: int,
    exc: Exception,
    retry_schedule: Optional[str] = None,
) -> None:
    """Schedule a task for a future retry by adding it to a sorted set."""
    error_type = classify_error(getattr(exc, "status_code", 0), str(exc))
    delay = calculate_retry_delay(retry_count, error_type, schedule_str=retry_schedule)
    retry_at_timestamp = time.time() + delay

    await update_task_state(
        redis_conn,
        task_id,
        "SCHEDULED",
        retry_count=retry_count + 1,
        last_error=str(exc),
        error_type=error_type,
        retry_after=datetime.fromtimestamp(retry_at_timestamp).isoformat(),
    )
    await redis_conn.zadd("tasks:scheduled", {task_id: retry_at_timestamp})


async def update_worker_heartbeat(redis_conn: aioredis.Redis, worker_id: str) -> None:
    """Update worker heartbeat in Redis."""
    heartbeat_key = f"worker:heartbeat:{worker_id}"
    current_time = time.time()
    await redis_conn.setex(heartbeat_key, 90, current_time)  # Expire after 90 seconds


# --- Celery Tasks ---------------------------------------------------------


@app.task(name="process_task", bind=True)
def process_task(self: Task, task_id: str) -> str:
    """
    Main task processor that handles different task types.

    Uses the GenericAPIExecutor to make API calls based on the task type
    configuration stored in Redis.
    """
    retry_count = self.request.retries
    worker_id = f"celery-{self.request.hostname}-{os.getpid()}"

    async def _run_task():
        nonlocal _retry_schedule
        redis_conn = await get_async_redis_connection()

        # Update heartbeat at start of task
        await update_worker_heartbeat(redis_conn, worker_id)

        data = await redis_conn.hgetall(f"task:{task_id}")
        if not data:
            raise PermanentError(f"Task {task_id} not found in Redis.")

        content = data.get("content", "")
        task_type = data.get("task_type", "")

        if not content:
            raise PermanentError("No content to process.")
        if not task_type:
            raise PermanentError("No task_type specified.")

        # Check for max retries before execution
        if retry_count >= settings.max_retries:
            raise PermanentError(f"Max retries ({settings.max_retries}) exceeded.")

        # Get task type config from Redis
        type_config = await redis_conn.hgetall(f"task_type:{task_type}")
        if not type_config:
            raise PermanentError(f"Task type '{task_type}' not found in configuration.")
        if type_config.get("enabled", "true") != "true":
            raise PermanentError(f"Task type '{task_type}' is disabled.")

        # Capture per-type retry schedule for error handling
        _retry_schedule = type_config.get("retry_schedule", "")

        await update_task_state(redis_conn, task_id, "ACTIVE", worker_id=worker_id)

        # Rate limiting (per task_type)
        rate_limit_timeout = 60.0
        if not await wait_for_rate_limit_token(task_type, timeout=rate_limit_timeout):
            raise TransientError("Rate limit token timeout")

        # Execute via generic executor
        executor = GenericAPIExecutor()
        task_data = {
            "content": content,
            "params": json.loads(data.get("params", "{}")),
        }
        result: ExecutionResult = await executor.execute(type_config, task_data)

        if not result.success:
            # The executor returned an error result
            error_class = result.error_type or "TransientError"
            if error_class == "PermanentError":
                raise PermanentError(result.error)
            elif error_class == "DependencyError":
                raise DependencyError(result.error)
            else:
                raise TransientError(result.error)

        await update_task_state(
            redis_conn,
            task_id,
            "COMPLETED",
            result=str(result.result),
            http_status=str(result.http_status) if result.http_status else "",
            completed_at=datetime.now(UTC).isoformat(),
        )

        # Fix #3: Fire callback URL if configured
        callback_url = data.get("callback_url")
        if callback_url:
            try:
                import httpx
                async with httpx.AsyncClient(timeout=10) as client:
                    await client.post(callback_url, json={
                        "task_id": task_id,
                        "state": "COMPLETED",
                        "result": result.result,
                        "http_status": result.http_status,
                        "completed_at": datetime.now(UTC).isoformat(),
                    })
            except Exception as cb_err:
                print(f"Warning: Callback to {callback_url} failed: {cb_err}")

        # Update heartbeat at end of task
        await update_worker_heartbeat(redis_conn, worker_id)

        return f"Task {task_id} ({task_type}) completed successfully."

    async def _handle_error(exc, error_type="TransientError", retry_schedule=None):
        """Handle task errors with proper Redis connection."""
        redis_conn = await get_async_redis_connection()

        # Classify the error to determine proper handling
        error_classification = classify_error(getattr(exc, "status_code", 0), str(exc))

        if error_type == "PermanentError" or error_classification in [
            "PermanentError",
            "DependencyError",
        ]:
            dlq_reason = (
                "DependencyError"
                if error_classification == "DependencyError"
                else "PermanentError"
            )
            await move_to_dlq(redis_conn, task_id, str(exc), dlq_reason)
            return f"Task {task_id} moved to DLQ ({dlq_reason}): {exc}"
        else:
            await schedule_task_for_retry(
                redis_conn, task_id, retry_count, exc, retry_schedule=retry_schedule
            )
            return f"Task {task_id} failed, scheduled for retry."

    # Extract retry_schedule from config (available after _run_task reads it)
    _retry_schedule = None

    async def _run_task_with_config():
        nonlocal _retry_schedule
        result = await _run_task()
        return result

    try:
        return asyncio.run(_run_task_with_config())
    except PermanentError as e:
        return asyncio.run(_handle_error(e, "PermanentError", retry_schedule=_retry_schedule))
    except TransientError as e:
        return asyncio.run(_handle_error(e, "TransientError", retry_schedule=_retry_schedule))
    except DependencyError as e:
        return asyncio.run(_handle_error(e, "DependencyError", retry_schedule=_retry_schedule))
    except Exception as e:
        # Catch any other unexpected errors and treat them as transient
        exc = TransientError(f"An unexpected error occurred: {str(e)}")
        return asyncio.run(_handle_error(exc, "TransientError", retry_schedule=_retry_schedule))


@app.task(name="process_scheduled_tasks")
def process_scheduled_tasks() -> str:
    """
    Periodically run by Celery Beat to move scheduled tasks back to the pending queue.
    """

    async def _run_processing():
        redis_conn = await get_async_redis_connection()

        now = time.time()
        due_tasks = await redis_conn.zrangebyscore(
            "tasks:scheduled", 0, now, start=0, num=100
        )

        if not due_tasks:
            return 0

        current_time = datetime.now(UTC).isoformat()

        # Move tasks to retry queue in a single pipeline (no nested pipelines)
        async with redis_conn.pipeline(transaction=True) as pipe:
            for task_id in due_tasks:
                pipe.lpush("tasks:pending:retry", task_id)
                pipe.zrem("tasks:scheduled", task_id)
                pipe.hset(f"task:{task_id}", mapping={
                    "state": "PENDING",
                    "updated_at": current_time,
                })
            await pipe.execute()

        return len(due_tasks)

    moved_count = asyncio.run(_run_processing())
    return f"Moved {moved_count} tasks from scheduled to retry queue."


# --- Queue Consumer Task --------------------------------------------------


def calculate_adaptive_retry_ratio(retry_depth: int) -> float:
    """Calculate adaptive retry ratio based on queue pressure."""
    if retry_depth < settings.retry_queue_warning:
        return settings.default_retry_ratio  # Normal: 30%
    elif retry_depth < settings.retry_queue_critical:
        return 0.2  # Warning: 20%
    else:
        return 0.1  # Critical: 10%


@app.task(name="consume_tasks", bind=True)
def consume_tasks(self: Task) -> str:
    """
    Consumer task that pulls task IDs from Redis queues and processes them.
    This runs in a continuous loop on each worker.
    """
    import logging
    import redis

    logger = logging.getLogger(__name__)
    logger.info(f"Starting task consumer on worker {self.request.hostname}")

    # Use synchronous Redis for BLPOP
    redis_conn = redis.from_url(settings.redis_url, decode_responses=True)

    processed_count = 0

    try:
        while True:
            try:
                # Get current retry queue depth for adaptive ratio
                retry_depth = redis_conn.llen("tasks:pending:retry")
                retry_ratio = calculate_adaptive_retry_ratio(retry_depth)

                # Decide which queue to check first based on retry ratio
                if random.random() > retry_ratio:
                    queues = ["tasks:pending:primary", "tasks:pending:retry"]
                else:
                    queues = ["tasks:pending:retry", "tasks:pending:primary"]

                # Use BLPOP to wait for a task ID from either queue (timeout: 5 seconds)
                result = redis_conn.blpop(queues, timeout=5)

                if result is None:
                    # Timeout occurred, continue loop (this is normal)
                    continue

                queue_name, task_id = result
                logger.info(f"Received task {task_id} from {queue_name}")

                # Trigger the actual task processing
                process_task.delay(task_id)

                processed_count += 1
                logger.info(
                    f"Dispatched task {task_id} for processing (total: {processed_count})"
                )

            except redis.RedisError as e:
                logger.error(f"Redis error in consumer: {e}")
                time.sleep(5)
                continue

            except Exception as e:
                logger.error(f"Unexpected error in consumer: {e}")
                time.sleep(1)
                continue

    except KeyboardInterrupt:
        logger.info("Consumer task interrupted, shutting down gracefully")
        return f"Consumer stopped after processing {processed_count} tasks"

    except Exception as e:
        logger.error(f"Consumer task failed: {e}")
        raise
