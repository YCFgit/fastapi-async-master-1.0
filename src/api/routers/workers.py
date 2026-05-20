# src/api/routers/workers.py
"""Worker management API endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request, status

from services import health_service

router = APIRouter(prefix="/api/v1/workers", tags=["workers-management"])


def get_health_service(request: Request):
    """Get health service from global variable or app state."""
    if health_service:
        return health_service
    return getattr(request.app.state, "health_service", None)


@router.get("/")
async def get_worker_status(
    request: Request,
    type_id: Optional[str] = Query(
        None, description="Filter circuit breaker status by task type"
    ),
) -> dict:
    """
    Get detailed health from all workers including circuit breaker status.

    Uses Redis heartbeats for basic connectivity and optionally filters
    circuit breaker status by task type.

    - **type_id**: Optional task type to get circuit breaker status for
    """
    try:
        current_health_service = get_health_service(request)

        if not current_health_service:
            return {
                "error": "Health service not initialized",
                "total_workers": 0,
                "timestamp": datetime.utcnow().isoformat(),
            }

        worker_details = []

        # Get all heartbeat keys
        heartbeat_keys = []
        async for key in current_health_service.redis_service.redis.scan_iter(
            "worker:heartbeat:*"
        ):
            heartbeat_keys.append(key)

        if not heartbeat_keys:
            return {
                "error": "No worker heartbeats found - workers may not be running",
                "total_workers": 0,
                "timestamp": datetime.utcnow().isoformat(),
            }

        import time
        current_time = time.time()

        for key in heartbeat_keys:
            worker_id = key.split(":", 2)[2]
            try:
                heartbeat_time = await current_health_service.redis_service.redis.get(key)
                if heartbeat_time:
                    heartbeat_timestamp = float(heartbeat_time)
                    age = current_time - heartbeat_timestamp
                    is_healthy = age < 60

                    worker_detail = {
                        "worker_id": worker_id,
                        "status": "healthy" if is_healthy else "stale",
                        "last_heartbeat": heartbeat_timestamp,
                        "heartbeat_age_seconds": round(age, 2),
                    }

                    # Get circuit breaker status if type_id specified
                    if type_id:
                        try:
                            from circuit_breaker import get_circuit_breaker_status
                            cb_status = get_circuit_breaker_status(type_id)
                            worker_detail["circuit_breaker"] = cb_status
                        except Exception as e:
                            worker_detail["circuit_breaker"] = {
                                "state": "unknown",
                                "error": str(e),
                            }
                    else:
                        worker_detail["circuit_breaker"] = {
                            "state": "unknown",
                            "note": "Specify type_id parameter to get circuit breaker status",
                        }

                    worker_details.append(worker_detail)
                else:
                    worker_details.append({
                        "worker_id": worker_id,
                        "status": "no_heartbeat",
                        "last_heartbeat": None,
                        "heartbeat_age_seconds": None,
                        "circuit_breaker": {"state": "unknown"},
                    })
            except (ValueError, TypeError) as e:
                worker_details.append({
                    "worker_id": worker_id,
                    "status": "error",
                    "error": str(e),
                    "circuit_breaker": {"state": "unknown"},
                })

        # Calculate summary statistics
        total_workers = len(worker_details)
        healthy_workers = sum(1 for w in worker_details if w.get("status") == "healthy")
        stale_workers = sum(1 for w in worker_details if w.get("status") == "stale")

        # Aggregate circuit breaker states
        circuit_breaker_states = {}
        for worker in worker_details:
            cb_state = worker.get("circuit_breaker", {}).get("state", "unknown")
            circuit_breaker_states[cb_state] = circuit_breaker_states.get(cb_state, 0) + 1

        return {
            "overall_status": "healthy"
            if healthy_workers == total_workers and total_workers > 0
            else "degraded",
            "total_workers": total_workers,
            "healthy_workers": healthy_workers,
            "stale_workers": stale_workers,
            "circuit_breaker_states": circuit_breaker_states,
            "worker_details": worker_details,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        return {
            "error": str(e),
            "total_workers": 0,
            "timestamp": datetime.utcnow().isoformat(),
        }


@router.post("/reset-circuit-breaker")
async def reset_circuit_breaker(
    type_id: str = Query(..., description="Task type to reset circuit breaker for"),
) -> dict:
    """
    Reset the circuit breaker for a specific task type.

    - **type_id**: The task type to reset the circuit breaker for

    This operates on the local worker's circuit breaker state.
    In a distributed setup, each worker maintains its own circuit breaker.
    """
    try:
        from circuit_breaker import reset_circuit_breaker as do_reset

        success = do_reset(type_id)
        return {
            "status": "success" if success else "failed",
            "type_id": type_id,
            "message": f"Circuit breaker reset for type '{type_id}'",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "type_id": type_id,
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


@router.post("/open-circuit-breaker")
async def open_circuit_breaker(
    type_id: str = Query(..., description="Task type to open circuit breaker for"),
) -> dict:
    """
    Open the circuit breaker for a specific task type to stop processing.

    - **type_id**: The task type to open the circuit breaker for

    Tasks of this type will be scheduled for retry rather than processed
    until the circuit breaker is reset.
    """
    try:
        from circuit_breaker import open_circuit_breaker as do_open

        success = do_open(type_id)
        return {
            "status": "success" if success else "failed",
            "type_id": type_id,
            "message": f"Circuit breaker opened for type '{type_id}'",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "type_id": type_id,
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }
