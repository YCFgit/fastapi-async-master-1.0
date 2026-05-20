"""Integration tests for task submission flow.

Tests the validation and construction of task submission requests
through the Pydantic schemas, verifying field validation, defaults,
and edge cases.
"""

import pytest
from pydantic import ValidationError

from api.schemas import (
    AuthType,
    QueueName,
    TaskState,
    TaskSubmitRequest,
    TaskTypeConfig,
)


# ---------------------------------------------------------------------------
# Tests: TaskSubmitRequest validation
# ---------------------------------------------------------------------------


class TestTaskSubmitRequestValidation:
    """Test that TaskSubmitRequest validates correctly."""

    @pytest.mark.asyncio
    async def test_submit_request_basic(self):
        """A minimal valid request should construct successfully."""
        request = TaskSubmitRequest(
            task_type="translate",
            content="Hello world",
        )
        assert request.task_type == "translate"
        assert request.content == "Hello world"
        assert request.params is None
        assert request.callback_url is None
        assert request.priority == 0  # default

    @pytest.mark.asyncio
    async def test_submit_request_with_params(self):
        """Request with params should preserve them."""
        request = TaskSubmitRequest(
            task_type="translate",
            content="Hello world",
            params={"target_lang": "zh", "formality": "formal"},
        )
        assert request.params == {"target_lang": "zh", "formality": "formal"}

    @pytest.mark.asyncio
    async def test_submit_with_callback_url(self):
        """Request should accept a callback_url."""
        request = TaskSubmitRequest(
            task_type="translate",
            content="Hello",
            callback_url="https://my-app.com/webhook",
        )
        assert request.callback_url == "https://my-app.com/webhook"

    @pytest.mark.asyncio
    async def test_submit_with_priority(self):
        """Request should accept an integer priority (0-10)."""
        request = TaskSubmitRequest(
            task_type="translate",
            content="Hello",
            priority=5,
        )
        assert request.priority == 5

    @pytest.mark.asyncio
    async def test_submit_priority_max(self):
        """Priority at the upper bound (10) should be accepted."""
        request = TaskSubmitRequest(
            task_type="translate",
            content="Hello",
            priority=10,
        )
        assert request.priority == 10

    @pytest.mark.asyncio
    async def test_submit_priority_default_zero(self):
        """Default priority should be 0."""
        request = TaskSubmitRequest(
            task_type="translate",
            content="Hello",
        )
        assert request.priority == 0


class TestTaskSubmitRequestEdgeCases:
    """Test edge cases and validation failures."""

    @pytest.mark.asyncio
    async def test_submit_empty_content_fails(self):
        """Empty content should fail validation (min_length=1)."""
        with pytest.raises(ValidationError):
            TaskSubmitRequest(task_type="translate", content="")

    @pytest.mark.asyncio
    async def test_submit_empty_task_type_fails(self):
        """Empty task_type should fail validation (min_length=1)."""
        with pytest.raises(ValidationError):
            TaskSubmitRequest(task_type="", content="Hello")

    @pytest.mark.asyncio
    async def test_submit_missing_task_type_fails(self):
        """Missing task_type should fail validation (required field)."""
        with pytest.raises(ValidationError):
            TaskSubmitRequest(content="Hello")

    @pytest.mark.asyncio
    async def test_submit_missing_content_fails(self):
        """Missing content should fail validation (required field)."""
        with pytest.raises(ValidationError):
            TaskSubmitRequest(task_type="translate")

    @pytest.mark.asyncio
    async def test_submit_priority_below_zero_fails(self):
        """Negative priority should fail validation (ge=0)."""
        with pytest.raises(ValidationError):
            TaskSubmitRequest(
                task_type="translate",
                content="Hello",
                priority=-1,
            )

    @pytest.mark.asyncio
    async def test_submit_priority_above_ten_fails(self):
        """Priority > 10 should fail validation (le=10)."""
        with pytest.raises(ValidationError):
            TaskSubmitRequest(
                task_type="translate",
                content="Hello",
                priority=11,
            )

    @pytest.mark.asyncio
    async def test_submit_with_complex_params(self):
        """Params can contain nested dicts and lists."""
        request = TaskSubmitRequest(
            task_type="translate",
            content="Hello",
            params={
                "target_lang": "zh",
                "options": {"formality": "formal", "glossary": ["term1", "term2"]},
            },
        )
        assert request.params["options"]["formality"] == "formal"
        assert len(request.params["options"]["glossary"]) == 2


# ---------------------------------------------------------------------------
# Tests: TaskTypeConfig validation
# ---------------------------------------------------------------------------


class TestTaskTypeConfigValidation:
    """Test that TaskTypeConfig validates correctly."""

    def test_basic_config(self):
        """A minimal valid config should construct successfully."""
        config = TaskTypeConfig(
            type_id="translate",
            name="Translation API",
            api_base_url="https://api.example.com",
            api_endpoint="/v1/translate",
        )
        assert config.type_id == "translate"
        assert config.http_method == "POST"  # default
        assert config.timeout == 30  # default
        assert config.max_retries == 3  # default
        assert config.enabled is True  # default
        assert config.auth_type == AuthType.NONE  # default

    def test_config_with_bearer_auth(self):
        """Bearer auth config should require 'token' key."""
        config = TaskTypeConfig(
            type_id="translate",
            name="Translation API",
            api_base_url="https://api.example.com",
            api_endpoint="/v1/translate",
            auth_type=AuthType.BEARER,
            auth_config={"token": "my-secret-token"},
        )
        assert config.auth_type == AuthType.BEARER
        assert config.auth_config["token"] == "my-secret-token"

    def test_config_bearer_auth_missing_token_fails(self):
        """Bearer auth without 'token' key should fail validation."""
        with pytest.raises(ValidationError, match="token"):
            TaskTypeConfig(
                type_id="translate",
                name="Translation API",
                api_base_url="https://api.example.com",
                api_endpoint="/v1/translate",
                auth_type=AuthType.BEARER,
                auth_config={"key": "wrong-key"},
            )

    def test_config_api_key_auth(self):
        """API key auth config should require 'header_name' and 'header_value'."""
        config = TaskTypeConfig(
            type_id="translate",
            name="Translation API",
            api_base_url="https://api.example.com",
            api_endpoint="/v1/translate",
            auth_type=AuthType.API_KEY,
            auth_config={"header_name": "X-API-Key", "header_value": "secret"},
        )
        assert config.auth_type == AuthType.API_KEY

    def test_config_basic_auth(self):
        """Basic auth config should require 'username' and 'password'."""
        config = TaskTypeConfig(
            type_id="translate",
            name="Translation API",
            api_base_url="https://api.example.com",
            api_endpoint="/v1/translate",
            auth_type=AuthType.BASIC,
            auth_config={"username": "user", "password": "pass"},
        )
        assert config.auth_type == AuthType.BASIC

    def test_config_invalid_base_url_fails(self):
        """api_base_url must start with http:// or https://."""
        with pytest.raises(ValidationError, match="http"):
            TaskTypeConfig(
                type_id="translate",
                name="Translation API",
                api_base_url="ftp://example.com",
                api_endpoint="/v1/translate",
            )

    def test_config_invalid_http_method_fails(self):
        """Invalid HTTP method should fail validation."""
        with pytest.raises(ValidationError, match="http_method"):
            TaskTypeConfig(
                type_id="translate",
                name="Translation API",
                api_base_url="https://api.example.com",
                api_endpoint="/v1/translate",
                http_method="INVALID",
            )

    def test_config_http_method_normalized_to_uppercase(self):
        """HTTP method should be normalized to uppercase."""
        config = TaskTypeConfig(
            type_id="translate",
            name="Translation API",
            api_base_url="https://api.example.com",
            api_endpoint="/v1/translate",
            http_method="get",
        )
        assert config.http_method == "GET"

    def test_config_base_url_trailing_slash_stripped(self):
        """Trailing slash should be stripped from api_base_url."""
        config = TaskTypeConfig(
            type_id="translate",
            name="Translation API",
            api_base_url="https://api.example.com/",
            api_endpoint="/v1/translate",
        )
        assert config.api_base_url == "https://api.example.com"


# ---------------------------------------------------------------------------
# Tests: Enum values
# ---------------------------------------------------------------------------


class TestEnums:
    """Test that enums have expected values."""

    def test_task_state_values(self):
        """TaskState should have all expected values."""
        assert TaskState.PENDING == "PENDING"
        assert TaskState.ACTIVE == "ACTIVE"
        assert TaskState.COMPLETED == "COMPLETED"
        assert TaskState.FAILED == "FAILED"
        assert TaskState.SCHEDULED == "SCHEDULED"
        assert TaskState.DLQ == "DLQ"

    def test_queue_name_values(self):
        """QueueName should have all expected values."""
        assert QueueName.PRIMARY == "primary"
        assert QueueName.RETRY == "retry"
        assert QueueName.SCHEDULED == "scheduled"
        assert QueueName.DLQ == "dlq"

    def test_auth_type_values(self):
        """AuthType should have all expected values."""
        assert AuthType.NONE == "none"
        assert AuthType.BEARER == "bearer"
        assert AuthType.API_KEY == "api_key"
        assert AuthType.BASIC == "basic"
