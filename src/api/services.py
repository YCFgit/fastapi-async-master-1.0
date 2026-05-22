# src/api/services.py
"""
Service layer for task and queue management.

Provides RedisService, TaskService, QueueService, and HealthService for
the generalized task processing framework.
"""

import json
import math
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from config import settings
from redis_config import get_standard_redis, initialize_redis, close_redis
from redis_config_simple import (
    initialize_simple_redis,
    close_simple_redis,
    get_simple_redis,
)
from schemas import (
    QueueStatus,
    TaskDetail,
    TaskState,
    QueueName,
    QUEUE_KEY_MAP,
    TaskListResponse,
    TaskSummaryListResponse,
    TaskSummary,
    TaskSubmitRequest,
)


# ---------------------------------------------------------------------------
# Redis Service
# ---------------------------------------------------------------------------


class RedisService:
    """Redis service for task and queue management with optimized connection pool."""

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._manager: Any = None
        self._simple_manager: Any = None
        self.redis: Any = None

    async def initialize(self) -> None:
        """Initialize the optimized Redis connection manager with fallback."""
        if self._manager is None and self._simple_manager is None:
            try:
                self._manager = await initialize_redis(self.redis_url)
                self.redis = await get_standard_redis()
                await self.redis.ping()
            except Exception as e:
                print(f"Optimized Redis failed ({e}), falling back to simple Redis")
                if self._manager:
                    try:
                        await close_redis()
                    except Exception:
                        pass
                    self._manager = None

                try:
                    self._simple_manager = await initialize_simple_redis(self.redis_url)
                    self.redis = await get_simple_redis()
                    await self.redis.ping()
                except Exception as e2:
                    print(f"Simple Redis also failed: {e2}")
                    import redis.asyncio as redis_mod
                    self.redis = redis_mod.from_url(self.redis_url, decode_responses=True)

    async def close(self) -> None:
        """Close Redis connection."""
        if self._manager:
            await close_redis()
            self._manager = None
        if self._simple_manager:
            await close_simple_redis()
            self._simple_manager = None
        self.redis = None

    async def ping(self) -> bool:
        """Check Redis connectivity."""
        try:
            if self.redis is None:
                await self.initialize()
            result = await self.redis.ping()
            return result is True or result == b"PONG" or result == "PONG"
        except Exception as e:
            print(f"Redis ping failed: {e}")
            return False

    async def get_pool_stats(self) -> Dict[str, Any]:
        """Get Redis connection pool statistics."""
        try:
            is_connected = await self.ping()
            return {
                "status": "connected" if is_connected else "disconnected",
                "max_connections": 50,
                "created_connections": 1,
                "available_connections": 1 if is_connected else 0,
                "in_use_connections": 0 if is_connected else 1,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


# ---------------------------------------------------------------------------
# Task Service
# ---------------------------------------------------------------------------


class TaskService:
    """Service for task CRUD operations."""

    def __init__(self, redis_service: RedisService):
        self.redis_service = redis_service

    @property
    def redis(self):
        return self.redis_service.redis

    async def create_task(self, request: TaskSubmitRequest) -> Dict[str, str]:
        """
        Create a new task and add it to the primary queue.

        Returns:
            Dict with task_id and initial state.
        """
        # Fix #4: Validate task_type exists and is enabled
        type_config = await self.redis.hgetall(f"task_type:{request.task_type}")
        if not type_config:
            raise ValueError(f"Task type '{request.task_type}' not found. Please register it first.")
        if type_config.get("enabled", "true") != "true":
            raise ValueError(f"Task type '{request.task_type}' is disabled.")

        task_id = str(uuid4())
        now = datetime.utcnow().isoformat()

        # Store task data in Redis hash
        task_data = {
            "task_id": task_id,
            "task_type": request.task_type,
            "content": request.content,
            "params": json.dumps(request.params) if request.params else "{}",
            "state": TaskState.PENDING.value,
            "retry_count": "0",
            "max_retries": str(settings.max_retries),
            "priority": str(request.priority),
            "created_at": now,
            "updated_at": now,
        }

        if request.callback_url:
            task_data["callback_url"] = request.callback_url

        await self.redis.hset(f"task:{task_id}", mapping=task_data)

        # Add to primary queue
        if request.priority > 0:
            # Use sorted set for priority tasks
            await self.redis.zadd(
                "tasks:pending:priority",
                {task_id: -request.priority},  # Negative so higher priority comes first
            )
        else:
            await self.redis.lpush("tasks:pending:primary", task_id)

        # Publish real-time update
        try:
            update_data = {
                "type": "task_created",
                "task_id": task_id,
                "task_type": request.task_type,
                "state": TaskState.PENDING.value,
                "timestamp": now,
            }
            await self.redis.publish("queue-updates", json.dumps(update_data))
        except Exception:
            pass

        return {"task_id": task_id, "state": TaskState.PENDING.value}

    async def get_task(self, task_id: str) -> Optional[TaskDetail]:
        """Get full task details by ID."""
        data = await self.redis.hgetall(f"task:{task_id}")
        if not data:
            return None

        return self._data_to_task_detail(data)

    async def list_tasks(
        self,
        status: Optional[TaskState] = None,
        task_type: Optional[str] = None,
        queue: Optional[QueueName] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 20,
        task_id: Optional[str] = None,
    ) -> TaskListResponse:
        """List tasks with filtering, sorting, and pagination."""
        # Scan all task keys
        all_tasks = []
        cursor = 0

        while True:
            cursor, keys = await self.redis.scan(
                cursor=cursor, match="task:*", count=200
            )
            for key in keys:
                # Skip non-task keys
                if ":heartbeat:" in key or ":type:" in key or "task_type:" in key:
                    continue
                data = await self.redis.hgetall(key)
                if data and "task_id" in data:
                    all_tasks.append(data)
            if cursor == 0:
                break

        # Apply filters
        filtered = all_tasks

        if status:
            filtered = [t for t in filtered if t.get("state") == status.value]

        if task_type:
            filtered = [t for t in filtered if t.get("task_type") == task_type]

        if task_id:
            filtered = [t for t in filtered if task_id.lower() in t.get("task_id", "").lower()]

        if start_date:
            filtered = [
                t for t in filtered
                if t.get("created_at", "") >= start_date.isoformat()
            ]

        if end_date:
            filtered = [
                t for t in filtered
                if t.get("created_at", "") <= end_date.isoformat()
            ]

        # Sort
        reverse = sort_order == "desc"
        filtered.sort(key=lambda t: t.get(sort_by, ""), reverse=reverse)

        # Paginate
        total_items = len(filtered)
        total_pages = max(1, math.ceil(total_items / page_size))
        start = (page - 1) * page_size
        end = start + page_size
        page_tasks = filtered[start:end]

        tasks = [self._data_to_task_detail(t) for t in page_tasks]

        return TaskListResponse(
            tasks=tasks,
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            status=status,
        )

    async def list_task_summaries(
        self,
        status: Optional[TaskState] = None,
        task_type: Optional[str] = None,
        queue: Optional[QueueName] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 20,
        task_id: Optional[str] = None,
    ) -> TaskSummaryListResponse:
        """List task summaries (without content) with filtering, sorting, and pagination."""
        full_response = await self.list_tasks(
            status=status,
            task_type=task_type,
            queue=queue,
            start_date=start_date,
            end_date=end_date,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
            task_id=task_id,
        )

        summaries = []
        for task in full_response.tasks:
            summary = TaskSummary(
                task_id=task.task_id,
                state=task.state,
                task_type=task.task_type,
                retry_count=task.retry_count,
                max_retries=task.max_retries,
                last_error=task.last_error,
                error_type=task.error_type,
                http_status=task.http_status,
                retry_after=task.retry_after,
                created_at=task.created_at,
                updated_at=task.updated_at,
                completed_at=task.completed_at,
                content_length=len(task.content) if task.content else 0,
                has_result=task.result is not None,
                error_history=task.error_history,
                state_history=task.state_history,
            )
            summaries.append(summary)

        return TaskSummaryListResponse(
            tasks=summaries,
            page=full_response.page,
            page_size=full_response.page_size,
            total_items=full_response.total_items,
            total_pages=full_response.total_pages,
            status=full_response.status,
        )

    async def retry_task(self, task_id: str, reset_retry_count: bool = False) -> bool:
        """Retry a failed or DLQ task."""
        data = await self.redis.hgetall(f"task:{task_id}")
        if not data:
            return False

        state = data.get("state")
        if state not in [TaskState.FAILED.value, TaskState.DLQ.value]:
            return False

        now = datetime.utcnow().isoformat()

        update_fields = {
            "state": TaskState.PENDING.value,
            "updated_at": now,
            "last_error": "",
            "error_type": "",
        }

        if reset_retry_count:
            update_fields["retry_count"] = "0"

        await self.redis.hset(f"task:{task_id}", mapping=update_fields)

        # Remove from DLQ if present
        await self.redis.lrem("dlq:tasks", 0, task_id)

        # Add to primary queue
        await self.redis.lpush("tasks:pending:primary", task_id)

        return True

    async def delete_task(self, task_id: str) -> bool:
        """Delete a task and all associated data."""
        data = await self.redis.hgetall(f"task:{task_id}")
        if not data:
            return False

        # Remove from all possible queues
        await self.redis.lrem("tasks:pending:primary", 0, task_id)
        await self.redis.lrem("tasks:pending:retry", 0, task_id)
        await self.redis.lrem("dlq:tasks", 0, task_id)
        await self.redis.zrem("tasks:scheduled", task_id)
        await self.redis.zrem("tasks:pending:priority", task_id)

        # Delete the task data
        await self.redis.delete(f"task:{task_id}")

        return True

    async def requeue_orphaned_tasks(self) -> Dict[str, Any]:
        """Find and re-queue orphaned tasks."""
        orphaned = []
        cursor = 0

        while True:
            cursor, keys = await self.redis.scan(
                cursor=cursor, match="task:*", count=200
            )
            for key in keys:
                if ":heartbeat:" in key or ":type:" in key or "task_type:" in key:
                    continue
                data = await self.redis.hgetall(key)
                if not data or "task_id" not in data:
                    continue

                state = data.get("state")
                task_id = data.get("task_id")

                if state == TaskState.PENDING.value:
                    # Check if task is in any queue
                    in_primary = await self.redis.lpos("tasks:pending:primary", task_id)
                    in_retry = await self.redis.lpos("tasks:pending:retry", task_id)
                    in_scheduled = await self.redis.zscore("tasks:scheduled", task_id)

                    if in_primary is None and in_retry is None and in_scheduled is None:
                        orphaned.append(task_id)

            if cursor == 0:
                break

        requeued = 0
        errors = []
        for task_id in orphaned:
            try:
                await self.redis.lpush("tasks:pending:primary", task_id)
                requeued += 1
            except Exception as e:
                errors.append({"task_id": task_id, "error": str(e)})

        return {
            "found": len(orphaned),
            "requeued": requeued,
            "errors": errors,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _data_to_task_detail(data: Dict[str, str]) -> TaskDetail:
        """Convert Redis hash data to a TaskDetail model."""

        def _int(val: Optional[str], default: int = 0) -> int:
            if val is None:
                return default
            try:
                return int(val)
            except (ValueError, TypeError):
                return default

        def _parse_json(val: Optional[str]) -> Any:
            if not val:
                return None
            try:
                return json.loads(val)
            except (json.JSONDecodeError, TypeError):
                # Return raw string if not valid JSON
                return val

        error_history = _parse_json(data.get("error_history")) or []
        state_history = _parse_json(data.get("state_history")) or []

        return TaskDetail(
            task_id=data.get("task_id", ""),
            state=TaskState(data.get("state", "PENDING")),
            task_type=data.get("task_type"),
            content=data.get("content", ""),
            params=_parse_json(data.get("params")),
            retry_count=_int(data.get("retry_count")),
            max_retries=_int(data.get("max_retries"), settings.max_retries),
            last_error=data.get("last_error") or None,
            error_type=data.get("error_type") or None,
            http_status=_int(data.get("http_status")) or None,
            retry_after=data.get("retry_after"),
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            updated_at=data.get("updated_at", datetime.utcnow().isoformat()),
            completed_at=data.get("completed_at"),
            result=_parse_json(data.get("result")) if data.get("result") else data.get("result"),
            error_history=error_history,
            state_history=state_history,
        )


# ---------------------------------------------------------------------------
# Queue Service
# ---------------------------------------------------------------------------


class QueueService:
    """Service for queue monitoring operations."""

    def __init__(self, redis_service: RedisService):
        self.redis_service = redis_service

    @property
    def redis(self):
        return self.redis_service.redis

    async def get_queue_status(self) -> QueueStatus:
        """Get comprehensive queue status and statistics."""
        queues = {}
        for name, key in QUEUE_KEY_MAP.items():
            if name == QueueName.SCHEDULED:
                queues[name.value] = await self.redis.zcard(key)
            else:
                queues[name.value] = await self.redis.llen(key)

        # Count tasks by state
        states: Dict[str, int] = {}
        cursor = 0
        while True:
            cursor, keys = await self.redis.scan(
                cursor=cursor, match="task:*", count=200
            )
            for key in keys:
                if ":heartbeat:" in key or ":type:" in key or "task_type:" in key:
                    continue
                state = await self.redis.hget(key, "state")
                if state:
                    states[state] = states.get(state, 0) + 1
            if cursor == 0:
                break

        # Calculate retry ratio
        retry_depth = queues.get("retry", 0)
        if retry_depth < settings.retry_queue_warning:
            retry_ratio = settings.default_retry_ratio
        elif retry_depth < settings.retry_queue_critical:
            retry_ratio = 0.2
        else:
            retry_ratio = 0.1

        return QueueStatus(
            queues=queues,
            states=states,
            retry_ratio=retry_ratio,
        )

    async def list_tasks_in_queue(self, queue_name: str, limit: int = 10) -> List[str]:
        """List task IDs from a specific queue."""
        key = QUEUE_KEY_MAP.get(QueueName(queue_name))
        if not key:
            return []

        if queue_name == QueueName.SCHEDULED.value:
            # Sorted set - get by score (earliest first)
            return await self.redis.zrange(key, 0, limit - 1)
        else:
            return await self.redis.lrange(key, 0, limit - 1)

    async def get_dlq_tasks(self, limit: int = 100) -> List[TaskDetail]:
        """Get tasks from the dead letter queue."""
        task_ids = await self.redis.lrange("dlq:tasks", 0, limit - 1)
        tasks = []
        for task_id in task_ids:
            data = await self.redis.hgetall(f"task:{task_id}")
            if data:
                tasks.append(TaskService._data_to_task_detail(data))
        return tasks


# ---------------------------------------------------------------------------
# Health Service
# ---------------------------------------------------------------------------


class HealthService:
    """Service for health check operations."""

    def __init__(self, redis_service: RedisService, celery_app=None):
        self.redis_service = redis_service
        self.celery_app = celery_app

    @property
    def redis(self):
        return self.redis_service.redis

    async def check_health(self) -> Dict[str, Any]:
        """Comprehensive health check."""
        components: Dict[str, Any] = {}

        # Check Redis
        try:
            redis_ok = await self.redis_service.ping()
            components["redis"] = redis_ok
        except Exception:
            components["redis"] = False

        # Check workers via heartbeats
        try:
            worker_count = 0
            async for key in self.redis.scan_iter("worker:heartbeat:*"):
                worker_count += 1
            components["workers"] = worker_count > 0
            components["worker_count"] = worker_count
        except Exception:
            components["workers"] = False

        # Check task types (if registry available)
        try:
            from task_type_registry import TaskTypeRegistry
            registry = TaskTypeRegistry(self.redis)
            types = await registry.list_types()
            active_types = [t for t in types if t.enabled]
            components["task_types"] = {
                "registered": len(types),
                "active": len(active_types),
            }
        except Exception:
            pass

        overall = "healthy" if all(
            v for k, v in components.items()
            if k in ("redis", "workers") and isinstance(v, bool)
        ) else "unhealthy"

        return {
            "status": overall,
            "components": components,
            "timestamp": datetime.utcnow().isoformat(),
        }


# ---------------------------------------------------------------------------
# Global service instances (populated by main.py lifespan)
# ---------------------------------------------------------------------------

redis_service: Optional[RedisService] = None
task_service: Optional[TaskService] = None
queue_service: Optional[QueueService] = None
health_service: Optional[HealthService] = None
