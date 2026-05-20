"""Tests for task_type_registry module - Task 9."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.schemas import AuthType, TaskTypeConfig, TaskTypeConfigResponse
from api.task_type_registry import TaskTypeRegistry


def make_config(type_id: str = "test_type", **kwargs) -> TaskTypeConfig:
    """Helper to create a TaskTypeConfig for testing."""
    defaults = {
        "type_id": type_id,
        "name": "Test Type",
        "description": "A test task type",
        "api_base_url": "https://api.example.com",
        "api_endpoint": "/v1/test",
        "http_method": "POST",
        "request_template": '{"text": "{{content}}"}',
        "request_headers": None,
        "response_jsonpath": "$.result",
        "response_parser": None,
        "auth_type": AuthType.NONE,
        "auth_config": None,
        "timeout": 30,
        "max_retries": 3,
        "rate_limit_requests": None,
        "rate_limit_interval": None,
        "circuit_breaker_enabled": True,
        "circuit_breaker_fail_max": None,
        "circuit_breaker_reset_timeout": None,
        "enabled": True,
    }
    defaults.update(kwargs)
    return TaskTypeConfig(**defaults)


class TestRegisterType:
    """Test register method."""

    @pytest.mark.asyncio
    async def test_register_type(self):
        """Registering a type should store it in Redis and add to active set."""
        mock_redis = AsyncMock()
        mock_redis.hset = AsyncMock()
        mock_redis.sadd = AsyncMock()

        registry = TaskTypeRegistry(mock_redis)
        config = make_config()

        result = await registry.register(config)

        assert result.type_id == "test_type"
        # Should call hset for the config hash
        mock_redis.hset.assert_called_once()
        call_args = mock_redis.hset.call_args
        assert call_args[0][0] == "task_type:test_type"
        # Should call sadd for the active set
        mock_redis.sadd.assert_called_once_with("task_types:active", "test_type")

    @pytest.mark.asyncio
    async def test_register_with_auth_config(self):
        """Registering with auth_config should serialize it as JSON."""
        mock_redis = AsyncMock()
        mock_redis.hset = AsyncMock()
        mock_redis.sadd = AsyncMock()

        registry = TaskTypeRegistry(mock_redis)
        config = make_config(
            auth_type=AuthType.BEARER,
            auth_config={"token": "my-secret-token"},
        )

        result = await registry.register(config)
        assert result.type_id == "test_type"


class TestGetType:
    """Test get method."""

    @pytest.mark.asyncio
    async def test_get_type(self):
        """Should return TaskTypeConfig when found in Redis."""
        mock_redis = AsyncMock()
        hash_data = {
            "type_id": "test_type",
            "name": "Test Type",
            "description": "A test task type",
            "api_base_url": "https://api.example.com",
            "api_endpoint": "/v1/test",
            "http_method": "POST",
            "request_template": '{"text": "{{content}}"}',
            "request_headers": "null",
            "response_jsonpath": "$.result",
            "response_parser": "null",
            "auth_type": "none",
            "auth_config": "null",
            "timeout": "30",
            "max_retries": "3",
            "rate_limit_requests": "null",
            "rate_limit_interval": "null",
            "circuit_breaker_enabled": "True",
            "circuit_breaker_fail_max": "null",
            "circuit_breaker_reset_timeout": "null",
            "enabled": "True",
        }
        mock_redis.hgetall = AsyncMock(return_value=hash_data)

        registry = TaskTypeRegistry(mock_redis)
        result = await registry.get("test_type")

        assert result is not None
        assert result.type_id == "test_type"
        assert result.name == "Test Type"
        assert result.api_base_url == "https://api.example.com"
        mock_redis.hgetall.assert_called_once_with("task_type:test_type")

    @pytest.mark.asyncio
    async def test_get_nonexistent_type(self):
        """Should return None when type not found in Redis."""
        mock_redis = AsyncMock()
        mock_redis.hgetall = AsyncMock(return_value={})

        registry = TaskTypeRegistry(mock_redis)
        result = await registry.get("nonexistent")

        assert result is None


class TestGetTypeResponse:
    """Test get_response method (without auth_config)."""

    @pytest.mark.asyncio
    async def test_get_response(self):
        """Should return TaskTypeConfigResponse without auth_config."""
        mock_redis = AsyncMock()
        hash_data = {
            "type_id": "test_type",
            "name": "Test Type",
            "description": "A test task type",
            "api_base_url": "https://api.example.com",
            "api_endpoint": "/v1/test",
            "http_method": "POST",
            "request_template": '{"text": "{{content}}"}',
            "request_headers": "null",
            "response_jsonpath": "$.result",
            "response_parser": "null",
            "auth_type": "none",
            "auth_config": '{"token": "secret"}',
            "timeout": "30",
            "max_retries": "3",
            "rate_limit_requests": "null",
            "rate_limit_interval": "null",
            "circuit_breaker_enabled": "True",
            "circuit_breaker_fail_max": "null",
            "circuit_breaker_reset_timeout": "null",
            "enabled": "True",
        }
        mock_redis.hgetall = AsyncMock(return_value=hash_data)

        registry = TaskTypeRegistry(mock_redis)
        result = await registry.get_response("test_type")

        assert result is not None
        assert isinstance(result, TaskTypeConfigResponse)
        # TaskTypeConfigResponse should not have auth_config
        assert not hasattr(result, "auth_config") or result.model_fields.get("auth_config") is None


class TestListTypes:
    """Test list_types method."""

    @pytest.mark.asyncio
    async def test_list_types(self):
        """Should list all types from active set."""
        mock_redis = AsyncMock()
        mock_redis.smembers = AsyncMock(return_value={"type1", "type2"})

        # Mock get for each type
        hash_data1 = {
            "type_id": "type1",
            "name": "Type 1",
            "description": "First type",
            "api_base_url": "https://api.example.com",
            "api_endpoint": "/v1/a",
            "http_method": "POST",
            "request_template": "null",
            "request_headers": "null",
            "response_jsonpath": "null",
            "response_parser": "null",
            "auth_type": "none",
            "auth_config": "null",
            "timeout": "30",
            "max_retries": "3",
            "rate_limit_requests": "null",
            "rate_limit_interval": "null",
            "circuit_breaker_enabled": "True",
            "circuit_breaker_fail_max": "null",
            "circuit_breaker_reset_timeout": "null",
            "enabled": "True",
        }
        hash_data2 = hash_data1.copy()
        hash_data2["type_id"] = "type2"
        hash_data2["name"] = "Type 2"
        hash_data2["api_endpoint"] = "/v1/b"

        mock_redis.hgetall = AsyncMock(side_effect=[hash_data1, hash_data2])

        registry = TaskTypeRegistry(mock_redis)
        result = await registry.list_types(active_only=True)

        assert len(result) == 2
        type_ids = {t.type_id for t in result}
        assert type_ids == {"type1", "type2"}


class TestDeleteType:
    """Test delete method."""

    @pytest.mark.asyncio
    async def test_delete_type(self):
        """Should delete from Redis and remove from active set."""
        mock_redis = AsyncMock()
        mock_redis.delete = AsyncMock(return_value=1)
        mock_redis.srem = AsyncMock()

        registry = TaskTypeRegistry(mock_redis)
        result = await registry.delete("test_type")

        assert result is True
        mock_redis.delete.assert_called_once_with("task_type:test_type")
        mock_redis.srem.assert_called_once_with("task_types:active", "test_type")

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self):
        """Should return False when type doesn't exist."""
        mock_redis = AsyncMock()
        mock_redis.delete = AsyncMock(return_value=0)
        mock_redis.srem = AsyncMock()

        registry = TaskTypeRegistry(mock_redis)
        result = await registry.delete("nonexistent")

        assert result is False


class TestIsActive:
    """Test is_active method."""

    @pytest.mark.asyncio
    async def test_is_active_true(self):
        """Should return True when type is in active set."""
        mock_redis = AsyncMock()
        mock_redis.sismember = AsyncMock(return_value=True)

        registry = TaskTypeRegistry(mock_redis)
        result = await registry.is_active("test_type")

        assert result is True
        mock_redis.sismember.assert_called_once_with("task_types:active", "test_type")

    @pytest.mark.asyncio
    async def test_is_active_false(self):
        """Should return False when type is not in active set."""
        mock_redis = AsyncMock()
        mock_redis.sismember = AsyncMock(return_value=False)

        registry = TaskTypeRegistry(mock_redis)
        result = await registry.is_active("test_type")

        assert result is False


class TestGetRawConfig:
    """Test get_raw_config method."""

    @pytest.mark.asyncio
    async def test_get_raw_config(self):
        """Should return raw dict for worker consumption."""
        mock_redis = AsyncMock()
        hash_data = {
            "api_base_url": "https://api.example.com",
            "api_endpoint": "/v1/test",
            "api_method": "POST",
            "api_timeout": "30",
            "auth_type": "none",
            "auth_config": "{}",
            "extra_headers": "{}",
            "request_template": '{"text": "{{content}}"}',
            "response_jsonpath": "$.result",
            "error_jsonpath": "",
            "retry_on_status": "",
        }
        mock_redis.hgetall = AsyncMock(return_value=hash_data)

        registry = TaskTypeRegistry(mock_redis)
        result = await registry.get_raw_config("test_type")

        assert result is not None
        assert isinstance(result, dict)
        assert result["api_base_url"] == "https://api.example.com"

    @pytest.mark.asyncio
    async def test_get_raw_config_nonexistent(self):
        """Should return None when not found."""
        mock_redis = AsyncMock()
        mock_redis.hgetall = AsyncMock(return_value={})

        registry = TaskTypeRegistry(mock_redis)
        result = await registry.get_raw_config("nonexistent")

        assert result is None
