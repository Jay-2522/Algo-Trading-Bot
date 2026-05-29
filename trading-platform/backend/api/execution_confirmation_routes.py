from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from backend.api.demo_execution_routes import demo_execution_service
from backend.api.multi_account_execution_routes import multi_account_execution_service
from backend.execution_confirmation.confirmation_service import ExecutionConfirmationService
from backend.utils.json_safety import safe_error_payload, to_json_safe


router = APIRouter(prefix="/execution-confirmation", tags=["Execution Confirmation"])
execution_confirmation_service = ExecutionConfirmationService(
    demo_result_store=demo_execution_service.result_store,
    multi_account_result_store=multi_account_execution_service.result_store,
)


@router.get("/status")
async def get_execution_confirmation_status() -> JSONResponse:
    try:
        return JSONResponse(content=to_json_safe(execution_confirmation_service.get_status()))
    except Exception as exc:
        return JSONResponse(content=safe_error_payload(f"Execution confirmation status unavailable: {exc}", "execution_confirmation"))


@router.get("/confirmations")
async def list_execution_confirmations(limit: int = Query(default=100, ge=1, le=1000)) -> JSONResponse:
    return JSONResponse(content=to_json_safe(execution_confirmation_service.list_confirmations(limit)))


@router.get("/confirmations/{execution_id}")
async def get_execution_confirmation(execution_id: str) -> JSONResponse:
    confirmation = execution_confirmation_service.get_confirmation(execution_id)
    if confirmation is None:
        raise HTTPException(status_code=404, detail="Execution confirmation not found.")
    return JSONResponse(content=to_json_safe(confirmation))


@router.post("/reconcile")
async def reconcile_execution_confirmations() -> JSONResponse:
    return JSONResponse(content=to_json_safe(execution_confirmation_service.reconcile_all()))


@router.get("/reconciliation-summary")
async def get_reconciliation_summary() -> JSONResponse:
    return JSONResponse(content=to_json_safe(execution_confirmation_service.reconciliation_summary()))


@router.get("/audit-events")
async def list_confirmation_audit_events(limit: int = Query(default=100, ge=1, le=1000)) -> JSONResponse:
    return JSONResponse(content=to_json_safe(execution_confirmation_service.audit_events(limit)))
