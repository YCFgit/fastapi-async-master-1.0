# src/api/schemas.py
"""Pydantic schemas for API request/response models."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class TaskState(str, Enum):
    """Task state enumeration."""

    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SCHEDULED = "SCHEDULED"
    DLQ = "DLQ"


class QueueName(str, Enum):
    """Enum for the different task queues."""

    PRIMARY = "primary"
    RETRY = "retry"
    SCHEDULED = "scheduled"
    DLQ = "dlq"


# Centralized mapping from queue names to Redis keys
QUEUE_KEY_MAP = {
    QueueName.PRIMARY: "tasks:pending:primary",
    QueueName.RETRY: "tasks:pending:retry",
    QueueName.SCHEDULED: "tasks:scheduled",
    QueueName.DLQ: "dlq:tasks",
}


class AuthType(str, Enum):
    """Authentication type enumeration."""

    NONE = "none"
    BEARER = "bearer"
    API_KEY = "api_key"
    BASIC = "basic"


class TaskTypeConfig(BaseModel):
    """Configuration for a task type that defines how to call an external API."""

    type_id: str = Field(
        ..., description="Unique identifier for the task type", min_length=1, max_length=64
    )
    name: str = Field(
        ..., description="Human-readable name for the task type", min_length=1, max_length=128
    )
    description: Optional[str] = Field(
        None, description="Description of what this task type does"
    )
    api_base_url: str = Field(
        ..., description="Base URL for the external API"
    )
    api_endpoint: str = Field(
        ..., description="API endpoint path (appended to base_url)"
    )
    http_method: str = Field(
        default="POST", description="HTTP method to use (GET, POST, PUT, etc.)"
    )
    request_template: Optional[str] = Field(
        None,
        description="Jinja2 template for the request body. "
        "Variables: {{content}}, {{params.*}}, {{task_id}}",
    )
    request_headers: Optional[Dict[str, str]] = Field(
        None, description="Additional headers to send with the API request"
    )
    response_jsonpath: Optional[str] = Field(
        None,
        description="JSONPath expression to extract the result from the API response",
    )
    error_jsonpath: Optional[str] = Field(
        None,
        description="JSONPath expression to extract error message from the API response",
    )
    status_jsonpath: Optional[str] = Field(
        None,
        description="JSONPath expression to extract status field from the API response",
    )
    response_parser: Optional[str] = Field(
        None,
        description="Name of a custom response parser function (alternative to jsonpath)",
    )
    auth_type: AuthType = Field(
        default=AuthType.NONE, description="Type of authentication to use"
    )
    auth_config: Optional[Dict[str, str]] = Field(
        None,
        description="Authentication configuration. Keys depend on auth_type: "
        "bearer -> {token}, api_key -> {header_name, header_value}, "
        "basic -> {username, password}",
    )
    timeout: int = Field(
        default=30,
        description="HTTP request timeout in seconds",
        ge=1,
        le=600,
    )
    max_retries: int = Field(
        default=3,
        description="Maximum number of retries for this task type",
        ge=0,
        le=10,
    )
    retry_on_status: Optional[str] = Field(
        None,
        description="Comma-separated HTTP status codes that trigger retries (e.g. '429,500,503')",
    )
    retry_schedule: Optional[str] = Field(
        None,
        description="Comma-separated retry delays in seconds (e.g. '5,15,60')",
    )
    rate_limit_requests: Optional[int] = Field(
        None,
        description="Number of requests allowed per rate_limit_interval",
        ge=1,
    )
    rate_limit_interval: Optional[int] = Field(
        None,
        description="Rate limit interval in seconds",
        ge=1,
    )
    circuit_breaker_enabled: bool = Field(
        default=True, description="Whether to enable circuit breaker for this task type"
    )
    circuit_breaker_fail_max: Optional[int] = Field(
        None,
        description="Max failures before circuit opens (overrides global setting)",
        ge=1,
    )
    circuit_breaker_reset_timeout: Optional[int] = Field(
        None,
        description="Seconds before circuit breaker resets (overrides global setting)",
        ge=1,
    )
    enabled: bool = Field(
        default=True, description="Whether this task type is active"
    )
    created_at: Optional[datetime] = Field(
        None, description="Timestamp when this config was created"
    )
    updated_at: Optional[datetime] = Field(
        None, description="Timestamp when this config was last updated"
    )

    @field_validator("api_base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Ensure base URL starts with http:// or https://."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("api_base_url must start with http:// or https://")
        return v.rstrip("/")

    @field_validator("http_method")
    @classmethod
    def validate_http_method(cls, v: str) -> str:
        """Ensure HTTP method is valid."""
        valid_methods = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
        upper = v.upper()
        if upper not in valid_methods:
            raise ValueError(f"http_method must be one of {valid_methods}")
        return upper

    @field_validator("auth_config")
    @classmethod
    def validate_auth_config(cls, v: Optional[Dict[str, str]], info) -> Optional[Dict[str, str]]:
        """Validate auth_config matches the auth_type."""
        if v is None:
            return v
        auth_type = info.data.get("auth_type", AuthType.NONE)
        if auth_type == AuthType.BEARER and "token" not in v:
            raise ValueError("auth_config for bearer auth must contain 'token'")
        if auth_type == AuthType.API_KEY:
            if "header_name" not in v or "header_value" not in v:
                raise ValueError(
                    "auth_config for api_key auth must contain 'header_name' and 'header_value'"
                )
        if auth_type == AuthType.BASIC:
            if "username" not in v or "password" not in v:
                raise ValueError(
                    "auth_config for basic auth must contain 'username' and 'password'"
                )
        return v


class TaskTypeConfigResponse(BaseModel):
    """Response model for task type configuration (without sensitive auth_config)."""

    type_id: str = Field(..., description="Unique identifier for the task type")
    name: str = Field(..., description="Human-readable name for the task type")
    description: Optional[str] = Field(None, description="Description of what this task type does")
    api_base_url: str = Field(..., description="Base URL for the external API")
    api_endpoint: str = Field(..., description="API endpoint path")
    http_method: str = Field(default="POST", description="HTTP method to use")
    request_template: Optional[str] = Field(None, description="Jinja2 template for the request body")
    request_headers: Optional[Dict[str, str]] = Field(None, description="Additional headers")
    response_jsonpath: Optional[str] = Field(None, description="JSONPath expression for response parsing")
    error_jsonpath: Optional[str] = Field(None, description="JSONPath for error message extraction")
    status_jsonpath: Optional[str] = Field(None, description="JSONPath for status field extraction")
    response_parser: Optional[str] = Field(None, description="Custom response parser function name")
    auth_type: AuthType = Field(default=AuthType.NONE, description="Type of authentication")
    timeout: int = Field(default=30, description="HTTP request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum number of retries")
    retry_on_status: Optional[str] = Field(None, description="HTTP status codes that trigger retries")
    retry_schedule: Optional[str] = Field(None, description="Retry delays in seconds")
    rate_limit_requests: Optional[int] = Field(None, description="Rate limit requests count")
    rate_limit_interval: Optional[int] = Field(None, description="Rate limit interval in seconds")
    circuit_breaker_enabled: bool = Field(default=True, description="Circuit breaker enabled")
    circuit_breaker_fail_max: Optional[int] = Field(None, description="Circuit breaker fail max")
    circuit_breaker_reset_timeout: Optional[int] = Field(None, description="Circuit breaker reset timeout")
    enabled: bool = Field(default=True, description="Whether this task type is active")
    created_at: Optional[datetime] = Field(None, description="Config creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Config last update timestamp")


class TaskTypeTestResult(BaseModel):
    """Result of testing a task type configuration."""

    success: bool = Field(..., description="Whether the test was successful")
    status_code: Optional[int] = Field(None, description="HTTP status code received")
    response_time_ms: Optional[float] = Field(None, description="Response time in milliseconds")
    request_sent: Optional[Dict[str, Any]] = Field(None, description="Request that was sent")
    response_body: Optional[Any] = Field(None, description="Response body received")
    extracted_result: Optional[Any] = Field(None, description="Result after applying jsonpath/parser")
    error: Optional[str] = Field(None, description="Error message if test failed")


class TaskSubmitRequest(BaseModel):
    """Schema for submitting a new task."""

    task_type: str = Field(
        ..., description="Type of task to execute (must match a registered task type)", min_length=1
    )
    content: str = Field(
        ..., description="Content to process", min_length=1
    )
    params: Optional[Dict[str, Any]] = Field(
        None, description="Additional parameters for the task"
    )
    callback_url: Optional[str] = Field(
        None, description="URL to call when task completes"
    )
    priority: int = Field(
        default=0,
        description="Task priority (higher = more urgent)",
        ge=0,
        le=10,
    )


class TaskResponse(BaseModel):
    """Schema for task creation response."""

    task_id: str = Field(..., description="Unique task identifier")
    state: TaskState = Field(..., description="Current task state")


class TaskDetail(BaseModel):
    """Schema for detailed task information."""

    task_id: str = Field(..., description="Unique task identifier")
    state: TaskState = Field(..., description="Current task state")
    task_type: Optional[str] = Field(None, description="Type of task")
    content: str = Field(..., description="Original text content")
    params: Optional[Dict[str, Any]] = Field(None, description="Task parameters")
    retry_count: int = Field(..., description="Number of retry attempts")
    max_retries: int = Field(..., description="Maximum allowed retries")
    last_error: Optional[str] = Field(None, description="Last error message")
    error_type: Optional[str] = Field(None, description="Type of last error")
    http_status: Optional[int] = Field(None, description="HTTP status code of last API call")
    retry_after: Optional[datetime] = Field(None, description="Next retry time")
    created_at: datetime = Field(..., description="Task creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    result: Optional[Any] = Field(None, description="Task result")
    error_history: List[Dict[str, Any]] = Field(
        default_factory=list, description="History of errors"
    )
    state_history: List[Dict[str, Any]] = Field(
        default_factory=list, description="History of state transitions"
    )


class TaskSummary(BaseModel):
    """Schema for task summary information (without content field)."""

    task_id: str = Field(..., description="Unique task identifier")
    state: TaskState = Field(..., description="Current task state")
    task_type: Optional[str] = Field(None, description="Type of task")
    retry_count: int = Field(..., description="Number of retry attempts")
    max_retries: int = Field(..., description="Maximum allowed retries")
    last_error: Optional[str] = Field(None, description="Last error message")
    error_type: Optional[str] = Field(None, description="Type of last error")
    http_status: Optional[int] = Field(None, description="HTTP status code of last API call")
    retry_after: Optional[datetime] = Field(None, description="Next retry time")
    created_at: datetime = Field(..., description="Task creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    content_length: Optional[int] = Field(
        None, description="Length of content in characters"
    )
    has_result: bool = Field(False, description="Whether task has a result")
    error_history: List[Dict[str, Any]] = Field(
        default_factory=list, description="History of errors"
    )
    state_history: List[Dict[str, Any]] = Field(
        default_factory=list, description="History of state transitions"
    )


class QueueStatus(BaseModel):
    """Schema for queue status information."""

    queues: Dict[str, int] = Field(..., description="Queue depths by name")
    states: Dict[str, int] = Field(..., description="Task counts by state")
    retry_ratio: float = Field(..., description="Current retry consumption ratio")


class HealthStatus(BaseModel):
    """Schema for health check response."""

    status: str = Field(..., description="Overall health status")
    components: Dict[str, Any] = Field(..., description="Component health status")
    note: Optional[str] = Field(None, description="Additional health information")
    timestamp: datetime = Field(..., description="Health check timestamp")


class ErrorResponse(BaseModel):
    """Schema for error responses."""

    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TaskRetryRequest(BaseModel):
    """Schema for manual task retry request."""

    reset_retry_count: bool = Field(
        default=False, description="Whether to reset the retry count"
    )


class TaskDeleteResponse(BaseModel):
    """Schema for task deletion response."""

    task_id: str = Field(..., description="Deleted task identifier")
    message: str = Field(..., description="Deletion confirmation message")


class TaskListResponse(BaseModel):
    """Schema for task list response."""

    tasks: List[TaskDetail] = Field(
        ..., description="List of tasks matching the criteria"
    )
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_items: int = Field(..., description="Total number of items")
    total_pages: int = Field(..., description="Total number of pages")
    status: Optional[TaskState] = Field(None, description="Filter status used")


class TaskSummaryListResponse(BaseModel):
    """Schema for task list response with summary information only."""

    tasks: List[TaskSummary] = Field(
        ..., description="List of task summaries matching the criteria"
    )
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_items: int = Field(..., description="Total number of items")
    total_pages: int = Field(..., description="Total number of pages")
    status: Optional[TaskState] = Field(None, description="Filter status used")
