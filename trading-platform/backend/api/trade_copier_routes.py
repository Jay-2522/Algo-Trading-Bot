from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query
from fastapi.responses import JSONResponse

from backend.trade_copier.trade_copier_service import TradeCopierService
from backend.trade_copier.copier_execution_bridge import CopierExecutionBridge
from backend.utils.json_safety import safe_error_payload, to_json_safe


router = APIRouter(prefix="/trade-copier", tags=["Demo Trade Copier"])
trade_copier_service = TradeCopierService()
copier_execution_bridge = CopierExecutionBridge(trade_copier_service=trade_copier_service)


@router.get("/status")
async def get_trade_copier_status() -> JSONResponse:
    try:
        return JSONResponse(content=to_json_safe(trade_copier_service.get_status()))
    except Exception as exc:
        return JSONResponse(content=safe_error_payload(f"Trade copier status unavailable: {exc}", "trade_copier"))


@router.get("/batches")
async def list_trade_copy_batches(limit: int = Query(default=100, ge=1, le=1000)) -> JSONResponse:
    return JSONResponse(content=to_json_safe(trade_copier_service.list_batches(limit)))


@router.get("/execution-results")
async def list_trade_copier_execution_results(limit: int = Query(default=100, ge=1, le=1000)) -> JSONResponse:
    return JSONResponse(content=to_json_safe(copier_execution_bridge.list_results(limit)))


@router.get("/execution-results/{copier_execution_id}")
async def get_trade_copier_execution_result(copier_execution_id: str) -> JSONResponse:
    result = copier_execution_bridge.get_result(copier_execution_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Trade copier execution result not found.")
    return JSONResponse(content=to_json_safe(result))


@router.get("/batches/{copy_batch_id}")
async def get_trade_copy_batch(copy_batch_id: str) -> JSONResponse:
    batch = trade_copier_service.get_batch(copy_batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Trade copy batch not found.")
    return JSONResponse(content=to_json_safe(batch))


@router.post("/preview-copy")
async def preview_trade_copy(payload: dict[str, Any] = Body(default_factory=dict)) -> JSONResponse:
    return JSONResponse(content=to_json_safe(trade_copier_service.preview_copy(payload)))


@router.post("/create-batch")
async def create_trade_copy_batch(payload: dict[str, Any] = Body(default_factory=dict)) -> JSONResponse:
    return JSONResponse(content=to_json_safe(trade_copier_service.create_copy_batch(payload)))


@router.post("/distribute-execution")
async def distribute_trade_copier_execution(payload: dict[str, Any] = Body(default_factory=dict)) -> JSONResponse:
    return JSONResponse(content=to_json_safe(copier_execution_bridge.distribute_execution(payload)))


@router.post("/batches/{copy_batch_id}/synchronize")
async def synchronize_trade_copy_batch(copy_batch_id: str) -> JSONResponse:
    summary = trade_copier_service.synchronize_batch(copy_batch_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Trade copy batch not found.")
    return JSONResponse(content=to_json_safe(summary))
