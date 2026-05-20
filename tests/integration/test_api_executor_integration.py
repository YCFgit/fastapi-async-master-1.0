"""Integration tests for the GenericAPIExecutor.

Tests the full API execution flow with mocked HTTP responses using respx,
verifying successful calls, error classification, auth header injection,
template rendering, and response parsing.
"""

import pytest
import httpx
import respx

from worker.api_executor import (
    DependencyError,
    ExecutionResult,
    GenericAPIExecutor,
    PermanentError,
    TransientError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(**overrides) -> dict:
    """Create a realistic task-type config dict (as stored in Redis)."""
    defaults = {
        "api_base_url": "https://api.example.com",
        "api_endpoint": "/v1/test",
        "http_method": "POST",
        "timeout": "30",
        "auth_type": "bearer",
        "auth_config": '{"token": "test-token"}',
        "request_headers": '{"Content-Type": "application/json"}',
        "request_template": '{"text": "{{content}}"}',
        "response_jsonpath": "$.result",
    }
    defaults.update(overrides)
    return defaults


def _make_task_data(content: str = "Hello world", **params) -> dict:
    """Create sample task data."""
    return {"content": content, "params": params}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGenericAPIExecutorIntegration:
    """Test the full API execution flow end-to-end."""

    def setup_method(self):
        self.executor = GenericAPIExecutor()

    # -- Successful execution -----------------------------------------------

    @respx.mock
    @pytest.mark.asyncio
    async def test_successful_execution_extracts_result(self):
        """A successful API call should extract the result via JSONPath."""
        respx.post("https://api.example.com/v1/test").mock(
            return_value=httpx.Response(
                200, json={"result": "Processed: Hello world"}
            )
        )

        config = _make_config()
        task_data = _make_task_data("Hello world")

        result = await self.executor.execute(config, task_data)

        assert result.success is True
        assert result.result == "Processed: Hello world"
        assert result.http_status == 200
        assert result.error is None
        assert result.latency_ms > 0

    @respx.mock
    @pytest.mark.asyncio
    async def test_successful_execution_without_jsonpath(self):
        """Without response_jsonpath, the raw response text is returned."""
        respx.post("https://api.example.com/v1/test").mock(
            return_value=httpx.Response(200, text="plain text response")
        )

        config = _make_config(response_jsonpath="")
        task_data = _make_task_data()

        result = await self.executor.execute(config, task_data)

        assert result.success is True
        assert "plain text response" in result.result

    @respx.mock
    @pytest.mark.asyncio
    async def test_successful_execution_with_nested_jsonpath(self):
        """Deeply nested JSONPath should extract the correct value."""
        respx.post("https://api.example.com/v1/test").mock(
            return_value=httpx.Response(
                200,
                json={"data": {"translations": [{"text": "Hola"}]}},
            )
        )

        config = _make_config(
            response_jsonpath="$.data.translations[0].text",
            request_template='{"q": "{{content}}"}',
        )
        task_data = _make_task_data("Hello")

        result = await self.executor.execute(config, task_data)

        assert result.success is True
        assert result.result == "Hola"

    # -- Permanent errors (non-retryable) -----------------------------------

    @respx.mock
    @pytest.mark.asyncio
    async def test_permanent_error_400(self):
        """400 Bad Request should classify as PermanentError."""
        respx.post("https://api.example.com/v1/test").mock(
            return_value=httpx.Response(400, text="Bad Request")
        )

        result = await self.executor.execute(_make_config(), _make_task_data())

        assert result.success is False
        assert result.http_status == 400
        assert result.error_type == "PermanentError"
        assert "400" in result.error

    @respx.mock
    @pytest.mark.asyncio
    async def test_permanent_error_401(self):
        """401 Unauthorized should classify as PermanentError."""
        respx.post("https://api.example.com/v1/test").mock(
            return_value=httpx.Response(
                401, json={"error": {"message": "Unauthorized"}}
            )
        )

        result = await self.executor.execute(_make_config(), _make_task_data())

        assert result.success is False
        assert result.http_status == 401
        assert result.error_type == "PermanentError"

    @respx.mock
    @pytest.mark.asyncio
    async def test_permanent_error_403(self):
        """403 Forbidden should classify as PermanentError."""
        respx.post("https://api.example.com/v1/test").mock(
            return_value=httpx.Response(403, text="Forbidden")
        )

        result = await self.executor.execute(_make_config(), _make_task_data())

        assert result.success is False
        assert result.error_type == "PermanentError"

    @respx.mock
    @pytest.mark.asyncio
    async def test_permanent_error_422(self):
        """422 Unprocessable Entity should classify as PermanentError."""
        respx.post("https://api.example.com/v1/test").mock(
            return_value=httpx.Response(422, text="Validation Error")
        )

        result = await self.executor.execute(_make_config(), _make_task_data())

        assert result.success is False
        assert result.error_type == "PermanentError"

    # -- Transient errors (retryable) ---------------------------------------

    @respx.mock
    @pytest.mark.asyncio
    async def test_transient_error_429(self):
        """429 Too Many Requests should classify as TransientError."""
        respx.post("https://api.example.com/v1/test").mock(
            return_value=httpx.Response(
                429, json={"error": {"message": "Rate limited"}}
            )
        )

        result = await self.executor.execute(_make_config(), _make_task_data())

        assert result.success is False
        assert result.http_status == 429
        assert result.error_type == "TransientError"

    @respx.mock
    @pytest.mark.asyncio
    async def test_transient_error_500(self):
        """500 Internal Server Error should classify as TransientError."""
        respx.post("https://api.example.com/v1/test").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )

        result = await self.executor.execute(_make_config(), _make_task_data())

        assert result.success is False
        assert result.http_status == 500
        assert result.error_type == "TransientError"

    @respx.mock
    @pytest.mark.asyncio
    async def test_transient_error_503(self):
        """503 Service Unavailable should classify as TransientError."""
        respx.post("https://api.example.com/v1/test").mock(
            return_value=httpx.Response(503, text="Service Unavailable")
        )

        result = await self.executor.execute(_make_config(), _make_task_data())

        assert result.success is False
        assert result.http_status == 503
        assert result.error_type == "TransientError"

    # -- Auth header injection ----------------------------------------------

    @respx.mock
    @pytest.mark.asyncio
    async def test_bearer_auth_header_sent(self):
        """Bearer token should be sent in the Authorization header."""
        route = respx.post("https://api.example.com/v1/test").mock(
            return_value=httpx.Response(200, json={"result": "ok"})
        )

        config = _make_config(auth_type="bearer", auth_config='{"token": "my-secret"}')
        await self.executor.execute(config, _make_task_data())

        request = route.calls.last.request
        assert request.headers["Authorization"] == "Bearer my-secret"

    @respx.mock
    @pytest.mark.asyncio
    async def test_no_auth_header_when_none(self):
        """With auth_type=none, no Authorization header should be sent."""
        route = respx.post("https://api.example.com/v1/test").mock(
            return_value=httpx.Response(200, json={"result": "ok"})
        )

        config = _make_config(auth_type="none", auth_config="{}")
        await self.executor.execute(config, _make_task_data())

        request = route.calls.last.request
        assert "Authorization" not in request.headers

    # -- Template rendering -------------------------------------------------

    @respx.mock
    @pytest.mark.asyncio
    async def test_template_renders_content(self):
        """Request template should render {{content}} with task data."""
        route = respx.post("https://api.example.com/v1/test").mock(
            return_value=httpx.Response(200, json={"result": "done"})
        )

        config = _make_config(
            request_template='{"input": "{{content}}", "target": "{{params.target_lang}}"}'
        )
        task_data = {"content": "Hello", "params": {"target_lang": "zh"}}

        await self.executor.execute(config, task_data)

        request = route.calls.last.request
        body = request.content
        assert b'"input"' in body
        assert b'"target"' in body

    # -- Error message includes status and body -----------------------------

    @respx.mock
    @pytest.mark.asyncio
    async def test_error_message_format(self):
        """Error message should contain the HTTP status code."""
        respx.post("https://api.example.com/v1/test").mock(
            return_value=httpx.Response(400, text="Invalid input")
        )

        result = await self.executor.execute(_make_config(), _make_task_data())

        assert result.success is False
        assert "400" in result.error
        assert "Invalid input" in result.error

    # -- GET method ---------------------------------------------------------

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_method(self):
        """Executor should support GET requests."""
        route = respx.get("https://api.example.com/v1/status").mock(
            return_value=httpx.Response(200, json={"result": "healthy"})
        )

        config = _make_config(
            api_endpoint="/v1/status",
            http_method="GET",
            request_template="",
        )
        result = await self.executor.execute(config, _make_task_data())

        assert result.success is True
        assert route.called

    # -- Custom headers -----------------------------------------------------

    @respx.mock
    @pytest.mark.asyncio
    async def test_custom_headers_sent(self):
        """Extra headers from config should be included in the request."""
        route = respx.post("https://api.example.com/v1/test").mock(
            return_value=httpx.Response(200, json={"result": "ok"})
        )

        config = _make_config(
            request_headers='{"X-Custom-Header": "custom-value"}'
        )
        await self.executor.execute(config, _make_task_data())

        request = route.calls.last.request
        assert request.headers["X-Custom-Header"] == "custom-value"
