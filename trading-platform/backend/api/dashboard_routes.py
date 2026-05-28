from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.dashboard.dashboard_service import DashboardService
from backend.utils.json_safety import safe_error_payload, to_json_safe


router = APIRouter(prefix="/dashboard", tags=["VPS Dashboard"])
dashboard_service = DashboardService()


@router.get("/status")
async def get_dashboard_status() -> JSONResponse:
    try:
        return JSONResponse(content=to_json_safe(dashboard_service.get_status()))
    except Exception as exc:
        return JSONResponse(content=safe_error_payload(f"Dashboard status unavailable: {exc}", "dashboard"))


@router.get("/overview")
async def get_dashboard_overview() -> JSONResponse:
    try:
        return JSONResponse(content=to_json_safe(dashboard_service.get_overview()))
    except Exception as exc:
        return JSONResponse(content=safe_error_payload(f"Dashboard overview unavailable: {exc}", "dashboard"))


@router.get("/cards")
async def get_dashboard_cards() -> JSONResponse:
    try:
        return JSONResponse(content=to_json_safe(dashboard_service.get_cards()))
    except Exception as exc:
        return JSONResponse(content=to_json_safe([safe_error_payload(f"Dashboard cards unavailable: {exc}", "dashboard")]))


@router.get("/summary")
async def get_dashboard_summary() -> JSONResponse:
    try:
        return JSONResponse(content=to_json_safe(dashboard_service.get_summary()))
    except Exception as exc:
        return JSONResponse(content=safe_error_payload(f"Dashboard summary unavailable: {exc}", "dashboard"))
