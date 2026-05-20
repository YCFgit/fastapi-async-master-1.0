"""Integration tests for task type CRUD operations.

Tests the full lifecycle of task types through the TaskTypeRegistry
using mocked Redis (AsyncMock), verifying create/read/update/delete
operations and edge cases.
"""

import json
import pytest
from unittest.mock import AsyncMock

from api.schemas import AuthType, TaskTypeConfig, TaskTypeConfigResponse
from api.task_type_registry import TaskTypeRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(type_id: str = "test_api", **overrides) -> TaskTypeConfig:
    """Create a TaskTypeConfig with sensible defaults for testing."""
    defaults = dict(
        type_id=type_id,
        name="Test API",
        description="A test API",
        api_base_url="https://api.example.com",
        api_endpoint="/v1/test",
        http_method="POST",
        request_template='{"text": "{{content}}"}',
        request_headers=None,
        response_jsonpath="$.result",
        response_parser=None,
        auth_type=AuthType.BEARER,
        auth_config={"token": "test-token"},
        timeout=30,
        max_retries=3,
        rate_limit_requests=None,
        rate_limit_interval=None,
        circuit_breaker_enabled=True,
        circuit_breaker_fail_max=None,
        circuit_breaker_reset_timeout=None,
        enabled=True,
    )
    defaults.update(overrides)
    return TaskTypeConfig(**defaults)


def _make_hash_data(type_id: str = "test_api", **overrides) -> dict:
    """Create realistic Redis hash data as the registry would store it."""
    defaults = {
        "type_id": type_id,
        "name": "Test API",
        "description": "A test API",
        "api_base_url": "https://api.example.com",
        "api_endpoint": "/v1/test",
        "http_method": "POST",
        "request_template": '{"text": "{{content}}"}',
        "request_headers": "null",
        "response_jsonpath": "$.result",
        "response_parser": "null",
        "auth_type": "bearer",
        "auth_config": '{"token": "test-token"}',
        "timeout": "30",
        "max_retries": "3",
        "rate_limit_requests": "null",
        "rate_limit_interval": "null",
        "circuit_breaker_enabled": "True",
        "circuit_breaker_fail_max": "null",
        "circuit_breaker_reset_timeout": "null",
        "enabled": "True",
        "created_at": "2025-01-01T00:00:00+00:00",
        "updated_at": "2025-01-01T00:00:00+00:00",
    }
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestTaskTypeCRUDIntegration:
    """Test full task type lifecycle: register, get, update, delete."""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock async Redis client."""
        redis = AsyncMock()
        redis.hset = AsyncMock()
        redis.hgetall = AsyncMock(return_value={})
        redis.hget = AsyncMock(return_value=None)
        redis.sadd = AsyncMock()
        redis.srem = AsyncMock()
        redis.smembers = AsyncMock(return_value=set())
        redis.sismember = AsyncMock(return_value=False)
        redis.delete = AsyncMock(return_value=0)
        redis.exists = AsyncMock(return_value=0)
        redis.scan = AsyncMock(return_value=(0, []))
        return redis

    @pytest.fixture
    def registry(self, mock_redis):
        return TaskTypeRegistry(mock_redis)

    # -- Register -----------------------------------------------------------

    @pytest.mark.asyncio
    async def test_register_stores_in_redis(self, registry, mock_redis):
        """Register should store config in Redis hash and add to active set."""
        config = _make_config()
        result = await registry.register(config)

        assert result.type_id == "test_api"
        mock_redis.hset.assert_called_once()
        call_args = mock_redis.hset.call_args
        # First positional arg is the key
        assert call_args[0][0] == "task_type:test_api"
        # mapping keyword arg should contain config fields
        mapping = call_args[1]["mapping"]
        assert mapping["type_id"] == "test_api"
        assert mapping["name"] == "Test API"
        mock_redis.sadd.assert_called_once_with("task_types:active", "test_api")

    @pytest.mark.asyncio
    async def test_register_with_auth_config(self, registry, mock_redis):
        """Auth config should be serialized as JSON in the hash mapping."""
        config = _make_config(auth_type=AuthType.BEARER, auth_config={"token": "secret"})
        await registry.register(config)

        mapping = mock_redis.hset.call_args[1]["mapping"]
        assert mapping["auth_type"] == "bearer"
        assert '"token"' in mapping["auth_config"]

    @pytest.mark.asyncio
    async def test_register_returns_config(self, registry, mock_redis):
        """Register should return the original TaskTypeConfig."""
        config = _make_config(type_id="my_type", name="My Type")
        result = await registry.register(config)

        assert isinstance(result, TaskTypeConfig)
        assert result.type_id == "my_type"
        assert result.name == "My Type"

    # -- Get ----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_existing_type(self, registry, mock_redis):
        """Getting an existing type should return a hydrated TaskTypeConfig."""
        mock_redis.hgetall.return_value = _make_hash_data()
        result = await registry.get("test_api")

        assert result is not None
        assert result.type_id == "test_api"
        assert result.name == "Test API"
        assert result.api_base_url == "https://api.example.com"
        assert result.auth_type == AuthType.BEARER
        mock_redis.hgetall.assert_called_once_with("task_type:test_api")

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(self, registry, mock_redis):
        """Getting a nonexistent type returns None."""
        mock_redis.hgetall.return_value = {}
        result = await registry.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_response_hides_auth_config(self, registry, mock_redis):
        """get_response should return TaskTypeConfigResponse without auth_config."""
        mock_redis.hgetall.return_value = _make_hash_data()
        result = await registry.get_response("test_api")

        assert result is not None
        assert isinstance(result, TaskTypeConfigResponse)
        # TaskTypeConfigResponse should not expose auth_config
        assert not hasattr(result, "auth_config") or "auth_config" not in result.model_fields

    @pytest.mark.asyncio
    async def test_get_response_nonexistent_returns_none(self, registry, mock_redis):
        """get_response returns None for nonexistent type."""
        mock_redis.hgetall.return_value = {}
        result = await registry.get_response("nonexistent")
        assert result is None

    # -- Update -------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_update_existing_type(self, registry, mock_redis):
        """Updating an existing type should store new config."""
        mock_redis.exists.return_value = 1
        mock_redis.hgetall.return_value = _make_hash_data()

        new_config = _make_config(name="Updated API")
        result = await registry.update("test_api", new_config)

        assert result.name == "Updated API"
        mock_redis.exists.assert_called_once_with("task_type:test_api")
        mock_redis.hset.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_nonexistent_raises_key_error(self, registry, mock_redis):
        """Updating a nonexistent type should raise KeyError."""
        mock_redis.exists.return_value = 0

        new_config = _make_config(name="Updated API")
        with pytest.raises(KeyError, match="not found"):
            await registry.update("nonexistent", new_config)

    @pytest.mark.asyncio
    async def test_update_disabled_type_removes_from_active_set(self, registry, mock_redis):
        """Disabling a type should remove it from the active set."""
        mock_redis.exists.return_value = 1
        mock_redis.hgetall.return_value = _make_hash_data()

        new_config = _make_config(enabled=False)
        await registry.update("test_api", new_config)

        mock_redis.srem.assert_called_once_with("task_types:active", "test_api")

    @pytest.mark.asyncio
    async def test_update_enabled_type_adds_to_active_set(self, registry, mock_redis):
        """Enabling a type should add it back to the active set."""
        mock_redis.exists.return_value = 1
        mock_redis.hgetall.return_value = _make_hash_data()

        new_config = _make_config(enabled=True)
        await registry.update("test_api", new_config)

        mock_redis.sadd.assert_called_once_with("task_types:active", "test_api")

    # -- Delete -------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_delete_existing_type(self, registry, mock_redis):
        """Deleting an existing type should return True and clean up Redis."""
        mock_redis.delete.return_value = 1

        result = await registry.delete("test_api")
        assert result is True
        mock_redis.delete.assert_called_once_with("task_type:test_api")
        mock_redis.srem.assert_called_once_with("task_types:active", "test_api")

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_false(self, registry, mock_redis):
        """Deleting a nonexistent type returns False."""
        mock_redis.delete.return_value = 0

        result = await registry.delete("nonexistent")
        assert result is False

    # -- Is Active ----------------------------------------------------------

    @pytest.mark.asyncio
    async def test_is_active_true(self, registry, mock_redis):
        """Should return True when type is in the active set."""
        mock_redis.sismember.return_value = True

        result = await registry.is_active("test_api")
        assert result is True
        mock_redis.sismember.assert_called_once_with("task_types:active", "test_api")

    @pytest.mark.asyncio
    async def test_is_active_false(self, registry, mock_redis):
        """Should return False when type is not in the active set."""
        mock_redis.sismember.return_value = False

        result = await registry.is_active("test_api")
        assert result is False

    # -- Get Raw Config -----------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_raw_config_returns_string_dict(self, registry, mock_redis):
        """get_raw_config should return a flat string-keyed dict."""
        mock_redis.hgetall.return_value = _make_hash_data()

        result = await registry.get_raw_config("test_api")
        assert result is not None
        assert isinstance(result, dict)
        assert result["api_base_url"] == "https://api.example.com"
        assert result["auth_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_get_raw_config_nonexistent(self, registry, mock_redis):
        """get_raw_config returns None for nonexistent type."""
        mock_redis.hgetall.return_value = {}
        result = await registry.get_raw_config("nonexistent")
        assert result is None

    # -- List Types ---------------------------------------------------------

    @pytest.mark.asyncio
    async def test_list_types_active_only(self, registry, mock_redis):
        """list_types(active_only=True) should query the active set."""
        mock_redis.smembers.return_value = {"type_a", "type_b"}
        mock_redis.hgetall.side_effect = [
            _make_hash_data(type_id="type_a", name="Type A"),
            _make_hash_data(type_id="type_b", name="Type B"),
        ]

        result = await registry.list_types(active_only=True)

        assert len(result) == 2
        type_ids = {t.type_id for t in result}
        assert type_ids == {"type_a", "type_b"}
        mock_redis.smembers.assert_called_once_with("task_types:active")

    @pytest.mark.asyncio
    async def test_list_types_scan_all(self, registry, mock_redis):
        """list_types(active_only=False) should scan for task_type:* keys."""
        mock_redis.scan = AsyncMock(
            return_value=(0, ["task_type:type_a", "task_type:type_b"])
        )
        mock_redis.hgetall.side_effect = [
            _make_hash_data(type_id="type_a", name="Type A"),
            _make_hash_data(type_id="type_b", name="Type B"),
        ]

        result = await registry.list_types(active_only=False)

        assert len(result) == 2
        mock_redis.scan.assert_called_once()

    # -- Full lifecycle (register -> get -> update -> delete) ----------------

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, mock_redis):
        """Test register -> get -> update -> delete in sequence."""
        registry = TaskTypeRegistry(mock_redis)
        config = _make_config()

        # 1. Register
        result = await registry.register(config)
        assert result.type_id == "test_api"

        # 2. Get (simulate Redis returning stored data)
        mock_redis.hgetall.return_value = _make_hash_data()
        got = await registry.get("test_api")
        assert got is not None
        assert got.name == "Test API"

        # 3. Update
        mock_redis.exists.return_value = 1
        updated_config = _make_config(name="Updated API", timeout=60)
        updated = await registry.update("test_api", updated_config)
        assert updated.name == "Updated API"
        assert updated.timeout == 60

        # 4. Delete
        mock_redis.delete.return_value = 1
        deleted = await registry.delete("test_api")
        assert deleted is True
