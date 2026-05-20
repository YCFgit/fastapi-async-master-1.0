# src/api/task_type_registry.py
"""CRUD operations for task type configurations in Redis."""

import json
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

import redis.asyncio as aioredis

try:
    from schemas import AuthType, TaskTypeConfig, TaskTypeConfigResponse
except ImportError:
    from api.schemas import AuthType, TaskTypeConfig, TaskTypeConfigResponse


class TaskTypeRegistry:
    """Registry for task type configurations stored in Redis.

    Redis keys:
        - ``task_type:{type_id}`` -- Hash storing config fields.
        - ``task_types:active``   -- Set of active type IDs.
    """

    def __init__(self, redis_client: aioredis.Redis):
        self._redis = redis_client

    # ------------------------------------------------------------------
    # CRUD operations
    # ------------------------------------------------------------------

    async def register(self, config: TaskTypeConfig) -> TaskTypeConfig:
        """Store a new task type configuration in Redis and mark it active.

        Args:
            config: The task type configuration to register.

        Returns:
            The registered TaskTypeConfig.
        """
        key = f"task_type:{config.type_id}"
        now = datetime.now(UTC).isoformat()

        mapping = self._config_to_hash(config, created_at=now, updated_at=now)

        await self._redis.hset(key, mapping=mapping)
        await self._redis.sadd("task_types:active", config.type_id)

        return config

    async def get(self, type_id: str) -> Optional[TaskTypeConfig]:
        """Read a task type configuration from Redis.

        Args:
            type_id: The task type identifier.

        Returns:
            TaskTypeConfig if found, None otherwise.
        """
        key = f"task_type:{type_id}"
        data = await self._redis.hgetall(key)

        if not data:
            return None

        return self._hash_to_config(data)

    async def get_response(self, type_id: str) -> Optional[TaskTypeConfigResponse]:
        """Get a task type config as a response model (without auth_config).

        Args:
            type_id: The task type identifier.

        Returns:
            TaskTypeConfigResponse if found, None otherwise.
        """
        config = await self.get(type_id)
        if config is None:
            return None

        return TaskTypeConfigResponse(
            type_id=config.type_id,
            name=config.name,
            description=config.description,
            api_base_url=config.api_base_url,
            api_endpoint=config.api_endpoint,
            http_method=config.http_method,
            request_template=config.request_template,
            request_headers=config.request_headers,
            response_jsonpath=config.response_jsonpath,
            error_jsonpath=config.error_jsonpath,
            status_jsonpath=config.status_jsonpath,
            response_parser=config.response_parser,
            auth_type=config.auth_type,
            timeout=config.timeout,
            max_retries=config.max_retries,
            retry_on_status=config.retry_on_status,
            retry_schedule=config.retry_schedule,
            rate_limit_requests=config.rate_limit_requests,
            rate_limit_interval=config.rate_limit_interval,
            circuit_breaker_enabled=config.circuit_breaker_enabled,
            circuit_breaker_fail_max=config.circuit_breaker_fail_max,
            circuit_breaker_reset_timeout=config.circuit_breaker_reset_timeout,
            enabled=config.enabled,
            created_at=config.created_at,
            updated_at=config.updated_at,
        )

    async def list_types(
        self, active_only: bool = False
    ) -> List[TaskTypeConfig]:
        """List all task type configurations.

        Args:
            active_only: If True, only return types in the active set.

        Returns:
            List of TaskTypeConfig.
        """
        if active_only:
            type_ids = await self._redis.smembers("task_types:active")
        else:
            # Scan for all task_type:* keys
            type_ids = set()
            cursor = 0
            while True:
                cursor, keys = await self._redis.scan(
                    cursor=cursor, match="task_type:*", count=100
                )
                for key in keys:
                    # key may be bytes or str depending on redis client
                    if isinstance(key, bytes):
                        key = key.decode()
                    type_ids.add(key.replace("task_type:", ""))
                if cursor == 0:
                    break

        results: List[TaskTypeConfig] = []
        for tid in type_ids:
            config = await self.get(tid)
            if config is not None:
                results.append(config)

        return results

    async def update(
        self, type_id: str, config: TaskTypeConfig
    ) -> TaskTypeConfig:
        """Update an existing task type configuration.

        Args:
            type_id: The task type identifier to update.
            config: The new configuration values.

        Returns:
            The updated TaskTypeConfig.

        Raises:
            KeyError: If the type_id does not exist.
        """
        key = f"task_type:{type_id}"
        exists = await self._redis.exists(key)
        if not exists:
            raise KeyError(f"Task type '{type_id}' not found")

        now = datetime.now(UTC).isoformat()

        # Preserve original created_at
        existing = await self._redis.hgetall(key)
        created_at = None
        if existing:
            val = existing.get("created_at") or existing.get(b"created_at")
            if val:
                created_at = val.decode() if isinstance(val, bytes) else val

        mapping = self._config_to_hash(
            config, created_at=created_at or now, updated_at=now
        )
        await self._redis.hset(key, mapping=mapping)

        # Ensure it's in the active set if enabled
        if config.enabled:
            await self._redis.sadd("task_types:active", type_id)
        else:
            await self._redis.srem("task_types:active", type_id)

        return config

    async def delete(self, type_id: str) -> bool:
        """Delete a task type configuration from Redis and the active set.

        Args:
            type_id: The task type identifier.

        Returns:
            True if the type was deleted, False if it did not exist.
        """
        key = f"task_type:{type_id}"
        deleted = await self._redis.delete(key)
        await self._redis.srem("task_types:active", type_id)
        return deleted > 0

    async def is_active(self, type_id: str) -> bool:
        """Check whether a task type is in the active set.

        Args:
            type_id: The task type identifier.

        Returns:
            True if active, False otherwise.
        """
        return bool(
            await self._redis.sismember("task_types:active", type_id)
        )

    async def get_raw_config(self, type_id: str) -> Optional[Dict[str, str]]:
        """Return the raw config dict for the worker.

        This is the flat string-keyed dict that GenericAPIExecutor.execute()
        expects.

        Args:
            type_id: The task type identifier.

        Returns:
            Dict of config fields, or None if not found.
        """
        key = f"task_type:{type_id}"
        data = await self._redis.hgetall(key)

        if not data:
            return None

        # Normalize bytes keys/values to str
        result: Dict[str, str] = {}
        for k, v in data.items():
            if isinstance(k, bytes):
                k = k.decode()
            if isinstance(v, bytes):
                v = v.decode()
            result[k] = v

        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _config_to_hash(
        config: TaskTypeConfig,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
    ) -> Dict[str, str]:
        """Convert a TaskTypeConfig to Redis hash fields.

        Complex types (dicts) are stored as JSON strings.
        """
        mapping: Dict[str, str] = {
            "type_id": config.type_id,
            "name": config.name,
            "description": config.description or "",
            "api_base_url": config.api_base_url,
            "api_endpoint": config.api_endpoint,
            "http_method": config.http_method,
            "request_template": config.request_template or "",
            "response_jsonpath": config.response_jsonpath or "",
            "error_jsonpath": config.error_jsonpath or "",
            "status_jsonpath": config.status_jsonpath or "",
            "response_parser": config.response_parser or "",
            "auth_type": (
                config.auth_type.value
                if isinstance(config.auth_type, AuthType)
                else config.auth_type
            ),
            "timeout": str(config.timeout),
            "max_retries": str(config.max_retries),
            "retry_on_status": config.retry_on_status or "",
            "retry_schedule": config.retry_schedule or "",
            "circuit_breaker_enabled": str(config.circuit_breaker_enabled).lower(),
            "enabled": str(config.enabled).lower(),
        }

        # Store complex types as JSON
        mapping["request_headers"] = (
            json.dumps(config.request_headers) if config.request_headers else "null"
        )
        mapping["auth_config"] = (
            json.dumps(config.auth_config) if config.auth_config else "null"
        )

        # Optional fields
        mapping["rate_limit_requests"] = (
            str(config.rate_limit_requests)
            if config.rate_limit_requests is not None
            else "null"
        )
        mapping["rate_limit_interval"] = (
            str(config.rate_limit_interval)
            if config.rate_limit_interval is not None
            else "null"
        )
        mapping["circuit_breaker_fail_max"] = (
            str(config.circuit_breaker_fail_max)
            if config.circuit_breaker_fail_max is not None
            else "null"
        )
        mapping["circuit_breaker_reset_timeout"] = (
            str(config.circuit_breaker_reset_timeout)
            if config.circuit_breaker_reset_timeout is not None
            else "null"
        )

        # Timestamps
        mapping["created_at"] = created_at or datetime.now(UTC).isoformat()
        mapping["updated_at"] = updated_at or datetime.now(UTC).isoformat()

        return mapping

    @staticmethod
    def _hash_to_config(data: Dict) -> TaskTypeConfig:
        """Convert a Redis hash to a TaskTypeConfig.

        Handles both bytes and str keys/values from Redis.
        """

        def _get(key: str, default: str = "") -> str:
            """Get a value from the hash, handling bytes keys."""
            val = data.get(key) or data.get(key.encode())
            if val is None:
                return default
            return val.decode() if isinstance(val, bytes) else val

        def _int_or_none(key: str) -> Optional[int]:
            val = _get(key, "")
            if not val or val == "null":
                return None
            return int(val)

        def _json_or_none(key: str) -> Optional[Any]:
            val = _get(key, "")
            if not val or val == "null":
                return None
            try:
                return json.loads(val)
            except (json.JSONDecodeError, ValueError):
                return None

        def _bool(key: str, default: bool = True) -> bool:
            val = _get(key, str(default))
            return val.lower() in ("true", "1", "yes")

        return TaskTypeConfig(
            type_id=_get("type_id"),
            name=_get("name"),
            description=_get("description") or None,
            api_base_url=_get("api_base_url"),
            api_endpoint=_get("api_endpoint"),
            http_method=_get("http_method", "POST"),
            request_template=_get("request_template") or None,
            request_headers=_json_or_none("request_headers"),
            response_jsonpath=_get("response_jsonpath") or None,
            error_jsonpath=_get("error_jsonpath") or None,
            status_jsonpath=_get("status_jsonpath") or None,
            response_parser=_get("response_parser") or None,
            auth_type=AuthType(_get("auth_type", "none")),
            auth_config=_json_or_none("auth_config"),
            timeout=int(_get("timeout", "30")),
            max_retries=int(_get("max_retries", "3")),
            retry_on_status=_get("retry_on_status") or None,
            retry_schedule=_get("retry_schedule") or None,
            rate_limit_requests=_int_or_none("rate_limit_requests"),
            rate_limit_interval=_int_or_none("rate_limit_interval"),
            circuit_breaker_enabled=_bool("circuit_breaker_enabled", True),
            circuit_breaker_fail_max=_int_or_none("circuit_breaker_fail_max"),
            circuit_breaker_reset_timeout=_int_or_none(
                "circuit_breaker_reset_timeout"
            ),
            enabled=_bool("enabled", True),
            created_at=_get("created_at") or None,
            updated_at=_get("updated_at") or None,
        )
