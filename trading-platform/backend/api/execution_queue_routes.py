from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query

from backend.execution_queue.execution_lifecycle_models import (
    ExecutionAuditEvent,
    OrderLifecycleState,
    SimulatedExecutionResult,
)
from backend.execution_queue.execution_queue_models import ExecutionQueueItem, ExecutionQueueStatus
from backend.execution_queue.execution_queue_service import ExecutionQueueService


router = APIRouter(prefix="/execution-queue", tags=["Execution Queue"])
execution_queue_service = ExecutionQueueService()


@router.get("/status", response_model=ExecutionQueueStatus)
async def get_execution_queue_status() -> ExecutionQueueStatus:
    return execution_queue_service.get_status()


@router.get("/lifecycle/status")
async def get_execution_lifecycle_status() -> dict:
    return execution_queue_service.get_lifecycle_status()


@router.get("/lifecycle/items", response_model=list[OrderLifecycleState])
async def get_execution_lifecycle_items() -> list[OrderLifecycleState]:
    return execution_queue_service.get_lifecycles()


@router.get("/lifecycle/audit-events", response_model=list[ExecutionAuditEvent])
async def get_execution_lifecycle_audit_events(
    limit: int = Query(default=100, ge=1, le=1000),
) -> list[ExecutionAuditEvent]:
    return execution_queue_service.get_audit_events(limit)


@router.get("/items", response_model=list[ExecutionQueueItem])
async def list_execution_queue_items(limit: int = Query(default=100, ge=1, le=1000)) -> list[ExecutionQueueItem]:
    return execution_queue_service.list_items(limit)


@router.get("/items/{queue_id}", response_model=ExecutionQueueItem)
async def get_execution_queue_item(queue_id: str) -> ExecutionQueueItem:
    item = execution_queue_service.get_item(queue_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Execution queue item not found.")
    return item


@router.post("/enqueue-preview", response_model=list[ExecutionQueueItem])
async def enqueue_execution_preview(payload: dict[str, Any] = Body(default_factory=dict)) -> list[ExecutionQueueItem]:
    return execution_queue_service.enqueue_preview(payload)


@router.post("/items/{queue_id}/simulate", response_model=SimulatedExecutionResult)
async def simulate_execution_queue_item(queue_id: str) -> SimulatedExecutionResult:
    result = execution_queue_service.simulate_queue_item(queue_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Execution queue item not found.")
    return result


@router.post("/simulate-latest", response_model=SimulatedExecutionResult)
async def simulate_latest_execution_queue_item() -> SimulatedExecutionResult:
    result = execution_queue_service.simulate_latest()
    if result is None:
        raise HTTPException(status_code=404, detail="No queued execution item available for simulation.")
    return result


@router.post("/items/{queue_id}/cancel", response_model=ExecutionQueueItem)
async def cancel_execution_queue_item(
    queue_id: str,
    payload: dict[str, Any] = Body(default_factory=dict),
) -> ExecutionQueueItem:
    item = execution_queue_service.cancel_item(queue_id, str(payload.get("reason") or "Cancelled by user request."))
    if item is None:
        raise HTTPException(status_code=404, detail="Execution queue item not found.")
    return item
