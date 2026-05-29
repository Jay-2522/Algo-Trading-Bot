from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.api.demo_execution_routes import demo_execution_service
from backend.api.execution_confirmation_routes import execution_confirmation_service
from backend.api.execution_risk_routes import execution_risk_service
from backend.api.multi_account_execution_routes import multi_account_execution_service
from backend.api.trade_copier_routes import trade_copier_service
from backend.execution_dashboard.execution_dashboard_builder import ExecutionDashboardBuilder
from backend.execution_dashboard.execution_dashboard_service import ExecutionDashboardService
from backend.utils.json_safety import safe_error_payload, to_json_safe


router = APIRouter(prefix="/execution-dashboard", tags=["Execution Dashboard"])
execution_dashboard_service = ExecutionDashboardService(
    builder=ExecutionDashboardBuilder(
        demo_execution_service=demo_execution_service,
        multi_account_execution_service=multi_account_execution_service,
        trade_copier_service=trade_copier_service,
        confirmation_service=execution_confirmation_service,
        execution_risk_service=execution_risk_service,
    )
)


@router.get("/status")
async def get_execution_dashboard_status() -> JSONResponse:
    try:
        return JSONResponse(content=to_json_safe(execution_dashboard_service.status()))
    except Exception as exc:
        return JSONResponse(content=safe_error_payload(f"Execution dashboard status unavailable: {exc}", "execution_dashboard"))


@router.get("/overview")
async def get_execution_dashboard_overview() -> JSONResponse:
    return JSONResponse(content=to_json_safe(execution_dashboard_service.overview()))


@router.get("/cards")
async def get_execution_dashboard_cards() -> JSONResponse:
    return JSONResponse(content=to_json_safe(execution_dashboard_service.cards()))


@router.get("/summary")
async def get_execution_dashboard_summary() -> JSONResponse:
    return JSONResponse(content=to_json_safe(execution_dashboard_service.summary()))
