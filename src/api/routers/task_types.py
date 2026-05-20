# src/api/routers/task_types.py
"""
Task Type Management API endpoints.

CRUD operations for task type configurations that define how the worker
processes different types of tasks (API endpoints, auth, templates, etc.).
"""

import time
from typing import List

import httpx
from fastapi import APIRouter, HTTPException, Request, status

from schemas import (
    TaskTypeConfig,
    TaskTypeConfigResponse,
    TaskTypeTestResult,
)
from task_type_registry import TaskTypeRegistry

router = APIRouter(prefix="/api/v1/task-types", tags=["task-types"])


async def _get_registry(request: Request) -> TaskTypeRegistry:
    """Get a TaskTypeRegistry instance using the current Redis connection."""
    from services import redis_service

    redis_client = None
    if redis_service and redis_service.redis:
        redis_client = redis_service.redis
    else:
        # Fallback to app state
        svc = getattr(request.app.state, "redis_service", None)
        if svc and svc.redis:
            redis_client = svc.redis

    if redis_client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis service not available",
        )

    return TaskTypeRegistry(redis_client)


def _config_to_response(config: TaskTypeConfig) -> TaskTypeConfigResponse:
    """Convert a TaskTypeConfig to a TaskTypeConfigResponse (without auth_config)."""
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
        response_parser=config.response_parser,
        auth_type=config.auth_type,
        timeout=config.timeout,
        max_retries=config.max_retries,
        rate_limit_requests=config.rate_limit_requests,
        rate_limit_interval=config.rate_limit_interval,
        circuit_breaker_enabled=config.circuit_breaker_enabled,
        circuit_breaker_fail_max=config.circuit_breaker_fail_max,
        circuit_breaker_reset_timeout=config.circuit_breaker_reset_timeout,
        enabled=config.enabled,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


@router.get("/", response_model=List[TaskTypeConfigResponse])
async def list_task_types(
    request: Request,
    include_inactive: bool = True,
) -> List[TaskTypeConfigResponse]:
    """
    List all registered task type configurations.

    - **include_inactive**: If false, only return active task types (default: true)
    """
    registry = await _get_registry(request)
    configs = await registry.list_types(active_only=not include_inactive)
    return [_config_to_response(c) for c in configs]


@router.post("/", response_model=TaskTypeConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_task_type(
    config: TaskTypeConfig,
    request: Request,
) -> TaskTypeConfigResponse:
    """
    Register a new task type configuration.

    The task type defines how the worker should call an external API to process
    tasks of this type, including endpoint, authentication, request template,
    and response parsing configuration.
    """
    registry = await _get_registry(request)

    # Check if already exists
    existing = await registry.get(config.type_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Task type '{config.type_id}' already exists",
        )

    try:
        registered = await registry.register(config)
        return _config_to_response(registered)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create task type: {str(e)}",
        )


@router.get("/{type_id}", response_model=TaskTypeConfigResponse)
async def get_task_type(
    type_id: str,
    request: Request,
) -> TaskTypeConfigResponse:
    """
    Get a task type configuration by ID.

    - **type_id**: The unique task type identifier
    """
    registry = await _get_registry(request)
    result = await registry.get_response(type_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task type '{type_id}' not found",
        )

    return result


@router.put("/{type_id}", response_model=TaskTypeConfigResponse)
async def update_task_type(
    type_id: str,
    config: TaskTypeConfig,
    request: Request,
) -> TaskTypeConfigResponse:
    """
    Update an existing task type configuration.

    - **type_id**: The unique task type identifier
    """
    # Ensure type_id in URL matches body
    if config.type_id != type_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="type_id in URL must match type_id in request body",
        )

    registry = await _get_registry(request)

    try:
        updated = await registry.update(type_id, config)
        return _config_to_response(updated)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task type '{type_id}' not found",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update task type: {str(e)}",
        )


@router.delete("/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task_type(
    type_id: str,
    request: Request,
) -> None:
    """
    Delete a task type configuration.

    - **type_id**: The unique task type identifier

    This will permanently remove the task type configuration. Active tasks
    of this type will continue to process but new tasks cannot be submitted.
    """
    registry = await _get_registry(request)
    deleted = await registry.delete(type_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task type '{type_id}' not found",
        )


@router.post("/{type_id}/activate", response_model=TaskTypeConfigResponse)
async def activate_task_type(
    type_id: str,
    request: Request,
) -> TaskTypeConfigResponse:
    """
    Activate a task type (enable it for processing).

    - **type_id**: The unique task type identifier
    """
    registry = await _get_registry(request)

    config = await registry.get(type_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task type '{type_id}' not found",
        )

    config.enabled = True
    updated = await registry.update(type_id, config)
    return _config_to_response(updated)


@router.post("/{type_id}/deactivate", response_model=TaskTypeConfigResponse)
async def deactivate_task_type(
    type_id: str,
    request: Request,
) -> TaskTypeConfigResponse:
    """
    Deactivate a task type (disable it for processing).

    - **type_id**: The unique task type identifier

    Active tasks will complete, but no new tasks of this type will be processed.
    """
    registry = await _get_registry(request)

    config = await registry.get(type_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task type '{type_id}' not found",
        )

    config.enabled = False
    updated = await registry.update(type_id, config)
    return _config_to_response(updated)


@router.post("/{type_id}/test", response_model=TaskTypeTestResult)
async def test_task_type(
    type_id: str,
    request: Request,
) -> TaskTypeTestResult:
    """
    Test a task type configuration by making a test API call.

    - **type_id**: The unique task type identifier

    Sends a test request to the configured API endpoint using the task type's
    configuration. Returns the response details for validation.
    """
    registry = await _get_registry(request)
    type_config = await registry.get(type_id)

    if not type_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task type '{type_id}' not found",
        )

    # Build the test request
    try:
        base_url = type_config.api_base_url.rstrip("/")
        endpoint = type_config.api_endpoint.lstrip("/")
        url = f"{base_url}/{endpoint}" if endpoint else base_url

        # Build headers
        headers = dict(type_config.request_headers) if type_config.request_headers else {}

        # Add auth headers
        if type_config.auth_type.value == "bearer" and type_config.auth_config:
            token = type_config.auth_config.get("token", "")
            headers["Authorization"] = f"Bearer {token}"
        elif type_config.auth_type.value == "api_key" and type_config.auth_config:
            header_name = type_config.auth_config.get("header_name", "X-API-Key")
            headers[header_name] = type_config.auth_config.get("header_value", "")

        # Build test body
        body = None
        if type_config.request_template:
            body = type_config.request_template.replace("{{content}}", "test content")

        start_time = time.time()

        async with httpx.AsyncClient() as client:
            method = type_config.http_method.upper()
            kwargs = {
                "headers": headers,
                "timeout": min(type_config.timeout, 30),
            }
            if body and method in ("POST", "PUT", "PATCH"):
                kwargs["content"] = body

            if method == "GET":
                response = await client.get(url, **kwargs)
            elif method == "POST":
                response = await client.post(url, **kwargs)
            elif method == "PUT":
                response = await client.put(url, **kwargs)
            else:
                response = await client.request(method, url, **kwargs)

        elapsed = (time.time() - start_time) * 1000

        # Parse response
        response_body = None
        extracted_result = None

        try:
            response_body = response.json()
            if type_config.response_jsonpath and response_body:
                try:
                    from response_parser import ResponseParser
                except ImportError:
                    from worker.response_parser import ResponseParser
                parser = ResponseParser()
                extracted_result = parser.extract(response_body, type_config.response_jsonpath)
        except Exception:
            response_body = response.text[:1000] if response.text else None

        return TaskTypeTestResult(
            success=200 <= response.status_code < 400,
            status_code=response.status_code,
            response_time_ms=round(elapsed, 2),
            request_sent={
                "url": url,
                "method": method,
                "headers": {k: v[:20] + "..." if len(str(v)) > 20 else str(v) for k, v in headers.items()},
            },
            response_body=response_body,
            extracted_result=extracted_result,
            error=None if 200 <= response.status_code < 400 else f"HTTP {response.status_code}",
        )

    except httpx.TimeoutException:
        return TaskTypeTestResult(
            success=False,
            error=f"Request timeout after {type_config.timeout}s",
        )
    except Exception as e:
        return TaskTypeTestResult(
            success=False,
            error=str(e),
        )
