# src/api/routers/tasks.py
"""
Generic task management API endpoints.

Provides unified task submission, listing, detail retrieval, retry, and deletion.
All task types are handled through a single endpoint -- the task_type field
determines how the worker will process the task.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from schemas import (
    TaskDeleteResponse,
    TaskDetail,
    TaskListResponse,
    TaskResponse,
    TaskRetryRequest,
    TaskState,
    TaskSubmitRequest,
    TaskSummaryListResponse,
    QueueName,
)
from services import TaskService

router = APIRouter(prefix="/api/v1/tasks", tags=["task-management"])


def get_task_service() -> TaskService:
    """Dependency to get task service from global or app state."""
    from services import task_service

    if task_service is not None:
        return task_service

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Task service not available",
    )


@router.post("/submit", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def submit_task(
    request: TaskSubmitRequest,
    task_svc: TaskService = Depends(get_task_service),
) -> TaskResponse:
    """
    Submit a new task for processing.

    The task will be queued for processing by a worker. The worker will use
    the task_type to look up the corresponding task type configuration and
    execute the appropriate API call.

    - **task_type**: The type of task (must match a registered task type)
    - **content**: The content to process
    - **params**: Additional parameters (optional)
    - **callback_url**: URL to call when task completes (optional)
    - **priority**: Task priority 0-10, higher is more urgent (default: 0)
    """
    try:
        result = await task_svc.create_task(request)
        return TaskResponse(
            task_id=result["task_id"],
            state=TaskState(result["state"]),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit task: {str(e)}",
        )


@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    task_status: Optional[TaskState] = Query(
        None, description="Filter tasks by status"
    ),
    task_type: Optional[str] = Query(
        None, description="Filter tasks by type"
    ),
    queue: Optional[QueueName] = Query(None, description="Filter tasks by queue"),
    start_date: Optional[datetime] = Query(
        None, description="Start date for filtering"
    ),
    end_date: Optional[datetime] = Query(None, description="End date for filtering"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order (asc or desc)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    task_id: Optional[str] = Query(None, description="Search by task ID"),
    task_svc: TaskService = Depends(get_task_service),
) -> TaskListResponse:
    """
    List tasks with full payloads, filtering, sorting, and pagination.
    """
    try:
        return await task_svc.list_tasks(
            status=task_status,
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
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tasks: {str(e)}",
        )


@router.get("/summaries/", response_model=TaskSummaryListResponse)
async def list_task_summaries(
    task_status: Optional[TaskState] = Query(
        None, description="Filter tasks by status"
    ),
    task_type: Optional[str] = Query(
        None, description="Filter tasks by type"
    ),
    queue: Optional[QueueName] = Query(None, description="Filter tasks by queue"),
    start_date: Optional[datetime] = Query(
        None, description="Start date for filtering"
    ),
    end_date: Optional[datetime] = Query(None, description="End date for filtering"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order (asc or desc)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    task_id: Optional[str] = Query(None, description="Search by task ID"),
    task_svc: TaskService = Depends(get_task_service),
) -> TaskSummaryListResponse:
    """
    List task summaries (without content field) with filtering, sorting, and pagination.
    """
    try:
        return await task_svc.list_task_summaries(
            status=task_status,
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
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list task summaries: {str(e)}",
        )


@router.get("/{task_id}", response_model=TaskDetail)
async def get_task(
    task_id: str,
    task_svc: TaskService = Depends(get_task_service),
) -> TaskDetail:
    """
    Get task status and details by ID.

    Returns complete task information including state, result, and error history.
    """
    task = await task_svc.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )
    return task


@router.post("/{task_id}/retry", response_model=TaskResponse)
async def retry_task(
    task_id: str,
    retry_request: Optional[TaskRetryRequest] = None,
    task_svc: TaskService = Depends(get_task_service),
) -> TaskResponse:
    """
    Manually retry a failed task.

    Only failed or DLQ tasks can be retried.
    """
    task = await task_svc.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )

    if task.state not in [TaskState.FAILED, TaskState.DLQ]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task in state '{task.state}' cannot be retried",
        )

    reset_retry_count = retry_request.reset_retry_count if retry_request else False
    success = await task_svc.retry_task(task_id, reset_retry_count)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to retry task"
        )

    return TaskResponse(task_id=task_id, state=TaskState.PENDING)


@router.post("/requeue-orphaned")
async def requeue_orphaned_tasks(
    task_svc: TaskService = Depends(get_task_service),
) -> dict:
    """
    Find and re-queue orphaned tasks.

    Orphaned tasks are tasks with PENDING state not present in any queue.
    """
    try:
        return await task_svc.requeue_orphaned_tasks()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to requeue orphaned tasks: {str(e)}",
        )


@router.delete("/{task_id}", response_model=TaskDeleteResponse)
async def delete_task(
    task_id: str,
    task_svc: TaskService = Depends(get_task_service),
) -> TaskDeleteResponse:
    """
    Delete a task and all associated data.

    This action cannot be undone.
    """
    try:
        success = await task_svc.delete_task(task_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
            )
        return TaskDeleteResponse(
            task_id=task_id,
            message=f"Task {task_id} and all associated data have been permanently deleted",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete task: {str(e)}",
        )
