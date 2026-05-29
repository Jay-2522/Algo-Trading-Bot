from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query
from fastapi.responses import JSONResponse

from backend.multi_account_execution.multi_account_execution_service import MultiAccountExecutionService
from backend.utils.json_safety import safe_error_payload, to_json_safe


router = APIRouter(prefix="/multi-account-execution", tags=["Multi-Account Demo Execution"])
multi_account_execution_service = MultiAccountExecutionService()


@router.get("/status")
async def get_multi_account_execution_status() -> JSONResponse:
    try:
        return JSONResponse(content=to_json_safe(multi_account_execution_service.get_status()))
    except Exception as exc:
        return JSONResponse(content=safe_error_payload(f"Multi-account execution status unavailable: {exc}", "multi_account_execution"))


@router.get("/results")
async def list_multi_account_execution_results(limit: int = Query(default=100, ge=1, le=1000)) -> JSONResponse:
    return JSONResponse(content=to_json_safe(multi_account_execution_service.list_results(limit)))


@router.get("/results/{batch_id}")
async def get_multi_account_execution_result(batch_id: str) -> JSONResponse:
    result = multi_account_execution_service.get_result(batch_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Multi-account demo execution batch not found.")
    return JSONResponse(content=to_json_safe(result))


@router.post("/preview-plans")
async def preview_multi_account_demo_plans(payload: dict[str, Any] = Body(default_factory=dict)) -> JSONResponse:
    return JSONResponse(content=to_json_safe(multi_account_execution_service.preview_plans(payload)))


@router.post("/execute-demo-batch")
async def execute_multi_account_demo_batch(payload: dict[str, Any] = Body(default_factory=dict)) -> JSONResponse:
    return JSONResponse(content=to_json_safe(multi_account_execution_service.execute_demo_batch(payload)))
