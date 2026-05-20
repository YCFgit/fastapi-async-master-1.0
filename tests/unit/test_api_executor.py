"""Tests for api_executor module - Task 8."""

import pytest
import httpx
import respx

from worker.api_executor import (
    DependencyError,
    ExecutionError,
    ExecutionResult,
    GenericAPIExecutor,
    PermanentError,
    TransientError,
)


class TestExceptionClasses:
    """Test exception hierarchy."""

    def test_execution_error_is_base(self):
        """All custom exceptions should inherit from ExecutionError."""
        assert issubclass(PermanentError, ExecutionError)
        assert issubclass(TransientError, ExecutionError)
        assert issubclass(DependencyError, ExecutionError)

    def test_can_raise_and_catch(self):
        """Exceptions should be catchable."""
        with pytest.raises(ExecutionError):
            raise PermanentError("test")
        with pytest.raises(ExecutionError):
            raise TransientError("test")
        with pytest.raises(ExecutionError):
            raise DependencyError("test")


class TestExecutionResult:
    """Test ExecutionResult dataclass."""

    def test_default_values(self):
        """Default values should be set correctly."""
        result = ExecutionResult(success=True)
        assert result.success is True
        assert result.result is None
        assert result.error is None
        assert result.error_type is None
        assert result.http_status is None
        assert result.latency_ms == 0

    def test_with_values(self):
        """All fields should be settable."""
        result = ExecutionResult(
            success=False,
            result="some result",
            error="some error",
            error_type="PermanentError",
            http_status=400,
            latency_ms=123.4,
        )
        assert result.success is False
        assert result.result == "some result"
        assert result.error == "some error"
        assert result.error_type == "PermanentError"
        assert result.http_status == 400
        assert result.latency_ms == 123.4


class TestBuildUrl:
    """Test _build_url helper."""

    def setup_method(self):
        self.executor = GenericAPIExecutor()

    def test_build_url_basic(self):
        """Should concatenate base URL and endpoint."""
        config = {
            "api_base_url": "https://api.example.com",
            "api_endpoint": "/v1/translate",
        }
        url = self.executor._build_url(config)
        assert url == "https://api.example.com/v1/translate"

    def test_build_url_no_trailing_slash(self):
        """Should handle base URL with trailing slash."""
        config = {
            "api_base_url": "https://api.example.com/",
            "api_endpoint": "/v1/translate",
        }
        url = self.executor._build_url(config)
        assert url == "https://api.example.com/v1/translate"


class TestParseRetrySchedule:
    """Test _parse_retry_schedule helper."""

    def setup_method(self):
        self.executor = GenericAPIExecutor()

    def test_parse_basic(self):
        """Should parse comma-separated seconds to list of floats."""
        result = self.executor._parse_retry_schedule("5,15,60")
        assert result == [5.0, 15.0, 60.0]

    def test_parse_single(self):
        """Should parse single value."""
        result = self.executor._parse_retry_schedule("10")
        assert result == [10.0]

    def test_parse_empty(self):
        """Should return empty list for empty string."""
        result = self.executor._parse_retry_schedule("")
        assert result == []

    def test_parse_with_spaces(self):
        """Should handle spaces around values."""
        result = self.executor._parse_retry_schedule("5, 15, 60")
        assert result == [5.0, 15.0, 60.0]


class TestParseRetryOnStatus:
    """Test _parse_retry_on_status helper."""

    def setup_method(self):
        self.executor = GenericAPIExecutor()

    def test_parse_basic(self):
        """Should parse comma-separated status codes."""
        result = self.executor._parse_retry_on_status("429,500,503")
        assert result == [429, 500, 503]

    def test_parse_single(self):
        """Should parse single status code."""
        result = self.executor._parse_retry_on_status("503")
        assert result == [503]

    def test_parse_empty(self):
        """Should return empty list for empty string."""
        result = self.executor._parse_retry_on_status("")
        assert result == []

    def test_parse_with_spaces(self):
        """Should handle spaces."""
        result = self.executor._parse_retry_on_status("429, 500, 503")
        assert result == [429, 500, 503]


class TestClassifyHttpStatus:
    """Test _classify_http_status helper."""

    def setup_method(self):
        self.executor = GenericAPIExecutor()

    def test_classify_http_status_permanent_400(self):
        """400 should be PermanentError."""
        error_class = self.executor._classify_http_status(400)
        assert error_class is PermanentError

    def test_classify_http_status_permanent_401(self):
        """401 should be PermanentError."""
        error_class = self.executor._classify_http_status(401)
        assert error_class is PermanentError

    def test_classify_http_status_permanent_403(self):
        """403 should be PermanentError."""
        error_class = self.executor._classify_http_status(403)
        assert error_class is PermanentError

    def test_classify_http_status_permanent_404(self):
        """404 should be PermanentError."""
        error_class = self.executor._classify_http_status(404)
        assert error_class is PermanentError

    def test_classify_http_status_permanent_405(self):
        """405 should be PermanentError."""
        error_class = self.executor._classify_http_status(405)
        assert error_class is PermanentError

    def test_classify_http_status_permanent_422(self):
        """422 should be PermanentError."""
        error_class = self.executor._classify_http_status(422)
        assert error_class is PermanentError

    def test_classify_http_status_transient_429(self):
        """429 should be TransientError."""
        error_class = self.executor._classify_http_status(429)
        assert error_class is TransientError

    def test_classify_http_status_transient_500(self):
        """500 should be TransientError."""
        error_class = self.executor._classify_http_status(500)
        assert error_class is TransientError

    def test_classify_http_status_transient_502(self):
        """502 should be TransientError."""
        error_class = self.executor._classify_http_status(502)
        assert error_class is TransientError

    def test_classify_http_status_transient_503(self):
        """503 should be TransientError."""
        error_class = self.executor._classify_http_status(503)
        assert error_class is TransientError

    def test_classify_http_status_transient_504(self):
        """504 should be TransientError."""
        error_class = self.executor._classify_http_status(504)
        assert error_class is TransientError


class TestClassifyErrorMessage:
    """Test _classify_error_message helper."""

    def setup_method(self):
        self.executor = GenericAPIExecutor()

    def test_classify_error_message_dependency_timeout(self):
        """Timeout error message should be DependencyError."""
        error_class = self.executor._classify_error_message("Connection timed out")
        assert error_class is DependencyError

    def test_classify_error_message_dependency_dns(self):
        """DNS resolution error should be DependencyError."""
        error_class = self.executor._classify_error_message("DNS resolution failed")
        assert error_class is DependencyError

    def test_classify_error_message_dependency_connection_refused(self):
        """Connection refused should be DependencyError."""
        error_class = self.executor._classify_error_message("Connection refused")
        assert error_class is DependencyError

    def test_classify_error_message_dependency_unavailable(self):
        """Service unavailable message should be DependencyError."""
        error_class = self.executor._classify_error_message("Service unavailable")
        assert error_class is DependencyError

    def test_classify_error_message_transient_default(self):
        """Unknown error should default to TransientError."""
        error_class = self.executor._classify_error_message("Something weird happened")
        assert error_class is TransientError


class TestBuildHeaders:
    """Test _build_headers helper."""

    def setup_method(self):
        self.executor = GenericAPIExecutor()

    def test_build_headers_no_auth(self):
        """No auth should produce Content-Type only."""
        config = {
            "auth_type": "none",
            "auth_config": "{}",
        }
        headers = self.executor._build_headers(config)
        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"

    def test_build_headers_bearer(self):
        """Bearer auth should produce Authorization header."""
        config = {
            "auth_type": "bearer",
            "auth_config": '{"token": "my-token"}',
        }
        headers = self.executor._build_headers(config)
        assert headers["Authorization"] == "Bearer my-token"

    def test_build_headers_extra_headers(self):
        """Extra headers should be merged."""
        config = {
            "auth_type": "none",
            "auth_config": "{}",
            "extra_headers": '{"X-Custom": "value"}',
        }
        headers = self.executor._build_headers(config)
        assert headers["X-Custom"] == "value"


class TestBuildBody:
    """Test _build_body helper."""

    def setup_method(self):
        self.executor = GenericAPIExecutor()

    def test_build_body_with_template(self):
        """Should render template with task_data."""
        config = {
            "request_template": '{"text": "{{content}}", "lang": "{{params.lang}}"}',
        }
        task_data = {"content": "Hello", "params": {"lang": "en"}}
        body = self.executor._build_body(config, task_data)
        assert body["text"] == "Hello"
        assert body["lang"] == "en"

    def test_build_body_no_template(self):
        """No template should return None."""
        config = {}
        task_data = {"content": "Hello", "params": {}}
        body = self.executor._build_body(config, task_data)
        assert body is None


class TestBuildQueryParams:
    """Test _build_query_params helper."""

    def setup_method(self):
        self.executor = GenericAPIExecutor()

    def test_build_query_params_api_key_in_query(self):
        """API key in query should produce query params."""
        config = {
            "auth_type": "api_key",
            "auth_config": '{"key": "my-key", "in": "query", "param_name": "api_key"}',
        }
        params = self.executor._build_query_params(config)
        assert params["api_key"] == "my-key"

    def test_build_query_params_no_auth(self):
        """No auth should return empty dict."""
        config = {
            "auth_type": "none",
            "auth_config": "{}",
        }
        params = self.executor._build_query_params(config)
        assert params == {}


class TestExecuteIntegration:
    """Integration tests for execute() using respx to mock HTTP."""

    def setup_method(self):
        self.executor = GenericAPIExecutor()

    @respx.mock
    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Successful API call should return ExecutionResult with result."""
        respx.post("https://api.example.com/v1/translate").mock(
            return_value=httpx.Response(
                200,
                json={"data": {"translated_text": "Hola"}},
            )
        )

        config = {
            "api_base_url": "https://api.example.com",
            "api_endpoint": "/v1/translate",
            "api_method": "POST",
            "api_timeout": "30",
            "auth_type": "none",
            "auth_config": "{}",
            "request_template": '{"text": "{{content}}"}',
            "response_jsonpath": "$.data.translated_text",
            "error_jsonpath": "",
            "retry_on_status": "",
            "extra_headers": "{}",
        }
        task_data = {"content": "Hello", "params": {}}

        result = await self.executor.execute(config, task_data)
        assert result.success is True
        assert result.result == "Hola"
        assert result.error is None
        assert result.http_status == 200
        assert result.latency_ms > 0

    @respx.mock
    @pytest.mark.asyncio
    async def test_execute_permanent_error(self):
        """400 response should return PermanentError."""
        respx.post("https://api.example.com/v1/translate").mock(
            return_value=httpx.Response(400, text="Bad Request")
        )

        config = {
            "api_base_url": "https://api.example.com",
            "api_endpoint": "/v1/translate",
            "api_method": "POST",
            "api_timeout": "30",
            "auth_type": "none",
            "auth_config": "{}",
            "request_template": '{"text": "{{content}}"}',
            "response_jsonpath": "",
            "error_jsonpath": "",
            "retry_on_status": "",
            "extra_headers": "{}",
        }
        task_data = {"content": "Hello", "params": {}}

        result = await self.executor.execute(config, task_data)
        assert result.success is False
        assert result.http_status == 400
        assert result.error_type == "PermanentError"

    @respx.mock
    @pytest.mark.asyncio
    async def test_execute_transient_error(self):
        """503 response should return TransientError."""
        respx.post("https://api.example.com/v1/translate").mock(
            return_value=httpx.Response(503, text="Service Unavailable")
        )

        config = {
            "api_base_url": "https://api.example.com",
            "api_endpoint": "/v1/translate",
            "api_method": "POST",
            "api_timeout": "30",
            "auth_type": "none",
            "auth_config": "{}",
            "request_template": '{"text": "{{content}}"}',
            "response_jsonpath": "",
            "error_jsonpath": "",
            "retry_on_status": "",
            "extra_headers": "{}",
        }
        task_data = {"content": "Hello", "params": {}}

        result = await self.executor.execute(config, task_data)
        assert result.success is False
        assert result.http_status == 503
        assert result.error_type == "TransientError"
