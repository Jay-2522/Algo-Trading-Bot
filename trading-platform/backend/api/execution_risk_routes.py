from typing import Any

from fastapi import APIRouter, Body, Query
from fastapi.responses import JSONResponse

from backend.execution_risk.execution_risk_service import ExecutionRiskService
from backend.utils.json_safety import safe_error_payload, to_json_safe


router = APIRouter(prefix="/execution-risk", tags=["Execution Risk"])
execution_risk_service = ExecutionRiskService()


@router.get("/status")
async def get_execution_risk_status() -> JSONResponse:
    try:
        return JSONResponse(content=to_json_safe(execution_risk_service.get_status()))
    except Exception as exc:
        return JSONResponse(content=safe_error_payload(f"Execution risk status unavailable: {exc}", "execution_risk"))


@router.get("/policy")
async def get_execution_risk_policy() -> JSONResponse:
    return JSONResponse(content=to_json_safe(execution_risk_service.get_policy()))


@router.post("/evaluate")
async def evaluate_execution_risk(payload: dict[str, Any] = Body(default_factory=dict)) -> JSONResponse:
    return JSONResponse(content=to_json_safe(execution_risk_service.evaluate(payload)))


@router.get("/decisions")
async def list_execution_risk_decisions(limit: int = Query(default=100, ge=1, le=1000)) -> JSONResponse:
    return JSONResponse(content=to_json_safe(execution_risk_service.list_decisions(limit)))


@router.get("/audit-events")
async def list_execution_risk_audit_events(limit: int = Query(default=100, ge=1, le=1000)) -> JSONResponse:
    return JSONResponse(content=to_json_safe(execution_risk_service.list_events(limit)))
