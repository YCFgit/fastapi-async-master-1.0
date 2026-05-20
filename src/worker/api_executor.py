# src/worker/api_executor.py
"""Generic API execution engine that calls any HTTP API based on configuration."""

import json
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Type

import httpx

try:
    from auth_handler import AuthConfig, AuthHandler
    from response_parser import ResponseParser
    from template_renderer import TemplateRenderer
except ImportError:
    # When imported from outside the worker directory (e.g. tests with pythonpath=src)
    from worker.auth_handler import AuthConfig, AuthHandler
    from worker.response_parser import ResponseParser
    from worker.template_renderer import TemplateRenderer


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class ExecutionError(Exception):
    """Base exception for all execution errors."""

    pass


class PermanentError(ExecutionError):
    """Error that should not be retried (e.g. 400, 401, 403, 404, 422)."""

    pass


class TransientError(ExecutionError):
    """Error that may succeed on retry (e.g. 429, 5xx, network blip)."""

    pass


class DependencyError(ExecutionError):
    """Error caused by an unavailable downstream dependency."""

    pass


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class ExecutionResult:
    """Result of a single API execution attempt.

    Attributes:
        success: Whether the execution succeeded.
        result: Extracted result value (from JSONPath extraction).
        error: Error message if execution failed.
        error_type: Class name of the exception type (e.g. "PermanentError").
        http_status: HTTP status code returned by the API.
        latency_ms: Round-trip time in milliseconds.
    """

    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    http_status: Optional[int] = None
    latency_ms: float = 0


# ---------------------------------------------------------------------------
# GenericAPIExecutor
# ---------------------------------------------------------------------------


class GenericAPIExecutor:
    """Execute arbitrary HTTP API calls driven by task-type configuration.

    Uses AuthHandler for authentication, TemplateRenderer for request body
    templating, and ResponseParser for JSONPath-based result extraction.
    """

    # HTTP status codes that are considered permanent (non-retryable) errors.
    _PERMANENT_STATUSES: set = {400, 401, 403, 404, 405, 422}

    # HTTP status codes that are considered transient (retryable) errors.
    _TRANSIENT_STATUSES: set = {429, 500, 502, 503, 504}

    # Substrings in error messages that indicate a dependency failure.
    _DEPENDENCY_PATTERNS: list = [
        "timeout",
        "timed out",
        "dns",
        "name resolution",
        "connection refused",
        "connection reset",
        "unavailable",
        "unreachable",
        "connect call failed",
        "network is unreachable",
    ]

    def __init__(self):
        self._auth_handler = AuthHandler()
        self._template_renderer = TemplateRenderer()
        self._response_parser = ResponseParser()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def execute(
        self,
        config: Dict[str, str],
        task_data: Dict[str, Any],
    ) -> ExecutionResult:
        """Execute an API call according to *config* and return the result.

        Parameters
        ----------
        config:
            Task-type configuration dict (keys like ``api_base_url``,
            ``api_endpoint``, ``auth_type``, etc.).
        task_data:
            Runtime data for this specific task (``content``, ``params``).

        Returns
        -------
        ExecutionResult
        """
        start = time.monotonic()

        url = self._build_url(config)
        headers = self._build_headers(config)
        query_params = self._build_query_params(config)
        body = self._build_body(config, task_data)

        method = config.get("http_method", config.get("api_method", "POST")).upper()
        timeout = int(config.get("timeout", config.get("api_timeout", "30")))

        try:
            status_code, response_text = await self._make_request(
                method=method,
                url=url,
                headers=headers,
                query_params=query_params,
                body=body,
                timeout=timeout,
            )
        except Exception as exc:
            latency_ms = (time.monotonic() - start) * 1000
            error_class = self._classify_error_message(str(exc))
            return ExecutionResult(
                success=False,
                error=str(exc),
                error_type=error_class.__name__,
                latency_ms=latency_ms,
            )

        latency_ms = (time.monotonic() - start) * 1000

        # Classify the HTTP status code.
        if status_code >= 400:
            error_class = self._classify_http_status(status_code)
            error_msg = f"HTTP {status_code}: {response_text[:500]}"
            return ExecutionResult(
                success=False,
                error=error_msg,
                error_type=error_class.__name__,
                http_status=status_code,
                latency_ms=latency_ms,
            )

        # Extract result from the response body.
        result = self._parse_response(config, status_code, response_text)
        return ExecutionResult(
            success=True,
            result=result,
            http_status=status_code,
            latency_ms=latency_ms,
        )

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    def _build_url(self, config: Dict[str, str]) -> str:
        """Concatenate ``api_base_url`` and ``api_endpoint``."""
        base = config.get("api_base_url", "").rstrip("/")
        endpoint = config.get("api_endpoint", "")
        return f"{base}{endpoint}"

    def _build_headers(self, config: Dict[str, str]) -> Dict[str, str]:
        """Parse extra headers JSON and merge with auth headers."""
        extra_headers: Dict[str, str] = {}
        extra_raw = config.get("request_headers", config.get("extra_headers", ""))
        if extra_raw:
            try:
                extra_headers = json.loads(extra_raw) if isinstance(extra_raw, str) else extra_raw
            except json.JSONDecodeError:
                pass

        auth_type = config.get("auth_type", "none")
        auth_config_raw = config.get("auth_config", "{}")
        if isinstance(auth_config_raw, dict):
            auth_config_dict = auth_config_raw
        elif isinstance(auth_config_raw, str):
            try:
                auth_config_dict = json.loads(auth_config_raw) if auth_config_raw else {}
            except json.JSONDecodeError:
                auth_config_dict = {}
        else:
            auth_config_dict = {}

        auth_config = AuthConfig(auth_type=auth_type, auth_config=auth_config_dict)
        headers = self._auth_handler.build_headers(auth_config, extra_headers)
        # Ensure Content-Type is present
        if "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"
        return headers

    def _build_query_params(self, config: Dict[str, str]) -> Dict[str, str]:
        """Build query parameters (for API key in query location)."""
        auth_type = config.get("auth_type", "none")
        auth_config_raw = config.get("auth_config", "{}")
        if isinstance(auth_config_raw, dict):
            auth_config_dict = auth_config_raw
        elif isinstance(auth_config_raw, str):
            try:
                auth_config_dict = json.loads(auth_config_raw) if auth_config_raw else {}
            except json.JSONDecodeError:
                auth_config_dict = {}
        else:
            auth_config_dict = {}

        auth_config = AuthConfig(auth_type=auth_type, auth_config=auth_config_dict)
        return self._auth_handler.build_query_params(auth_config)

    def _build_body(
        self, config: Dict[str, str], task_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Render the request body using the Jinja2 template.

        Returns None if no template is configured.
        """
        template_str = config.get("request_template", "")
        if not template_str:
            return None

        render_data = {
            "content": task_data.get("content", ""),
            "params": task_data.get("params", {}),
        }
        return self._template_renderer.render_json(template_str, render_data)

    async def _make_request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        query_params: Dict[str, str],
        body: Optional[Dict[str, Any]],
        timeout: int,
    ) -> tuple:
        """Perform the actual HTTP request using httpx.

        Returns (status_code, response_text).
        """
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                params=query_params,
                json=body,
            )
            return response.status_code, response.text

    def _parse_response(
        self, config: Dict[str, str], http_status: int, response_text: str
    ) -> Optional[Any]:
        """Extract the result from the response body using JSONPath."""
        jsonpath_expr = config.get("response_jsonpath", "")
        if not jsonpath_expr:
            return response_text

        data = self._response_parser.parse_raw_response(response_text)
        if data is None:
            return response_text

        return self._response_parser.extract(data, jsonpath_expr, strict=False)

    # ------------------------------------------------------------------
    # Classification helpers
    # ------------------------------------------------------------------

    def _classify_http_status(self, status_code: int) -> Type[ExecutionError]:
        """Classify an HTTP status code as permanent or transient.

        Returns the appropriate exception class.
        """
        if status_code in self._PERMANENT_STATUSES:
            return PermanentError
        if status_code in self._TRANSIENT_STATUSES:
            return TransientError
        # Default: 4xx -> permanent, 5xx -> transient
        if 400 <= status_code < 500:
            return PermanentError
        return TransientError

    def _classify_error_message(self, message: str) -> Type[ExecutionError]:
        """Classify an error message as dependency or transient.

        Checks for known dependency-related substrings.
        """
        lower = message.lower()
        for pattern in self._DEPENDENCY_PATTERNS:
            if pattern in lower:
                return DependencyError
        return TransientError

    # ------------------------------------------------------------------
    # Config parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_retry_schedule(schedule_str: str) -> List[float]:
        """Parse a comma-separated retry schedule string.

        Example: "5,15,60" -> [5.0, 15.0, 60.0]
        """
        if not schedule_str or not schedule_str.strip():
            return []
        return [float(x.strip()) for x in schedule_str.split(",") if x.strip()]

    @staticmethod
    def _parse_retry_on_status(status_str: str) -> List[int]:
        """Parse a comma-separated retry-on-status string.

        Example: "429,500,503" -> [429, 500, 503]
        """
        if not status_str or not status_str.strip():
            return []
        return [int(x.strip()) for x in status_str.split(",") if x.strip()]
