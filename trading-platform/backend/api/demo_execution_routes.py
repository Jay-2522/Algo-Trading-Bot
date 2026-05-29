from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query
from fastapi.responses import JSONResponse

from backend.api.execution_queue_routes import execution_queue_service
from backend.demo_execution.demo_execution_models import DemoExecutionRequest
from backend.demo_execution.demo_execution_service import DemoExecutionService
from backend.utils.json_safety import safe_error_payload, to_json_safe


router = APIRouter(prefix="/demo-execution", tags=["MT5 Demo Execution"])
demo_execution_service = DemoExecutionService(execution_queue_service=execution_queue_service)


@router.get("/status")
async def get_demo_execution_status() -> JSONResponse:
    try:
        return JSONResponse(content=to_json_safe(demo_execution_service.get_status()))
    except Exception as exc:
        return JSONResponse(content=safe_error_payload(f"Demo execution status unavailable: {exc}", "demo_execution"))


@router.get("/account-status")
async def get_demo_execution_account_status() -> JSONResponse:
    try:
        return JSONResponse(content=to_json_safe(demo_execution_service.verify_account()))
    except Exception as exc:
        return JSONResponse(content=safe_error_payload(f"Demo account verification unavailable: {exc}", "demo_execution"))


@router.get("/results")
async def list_demo_execution_results(limit: int = Query(default=100, ge=1, le=1000)) -> JSONResponse:
    return JSONResponse(content=to_json_safe(demo_execution_service.list_results(limit)))


@router.get("/results/{execution_id}")
async def get_demo_execution_result(execution_id: str) -> JSONResponse:
    result = demo_execution_service.get_result(execution_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Demo execution result not found.")
    return JSONResponse(content=to_json_safe(result))


@router.post("/queue/{queue_id}/execute-demo")
async def execute_demo_queue_item(
    queue_id: str,
    payload: dict[str, Any] = Body(default_factory=dict),
) -> JSONResponse:
    request = DemoExecutionRequest(queue_id=queue_id, **{key: value for key, value in payload.items() if key != "queue_id"})
    result = demo_execution_service.execute_queue_item_demo(queue_id, request)
    return JSONResponse(content=to_json_safe(result))
