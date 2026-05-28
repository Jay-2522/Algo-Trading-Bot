from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.demo_mode.client_demo_service import ClientDemoService
from backend.utils.json_safety import safe_error_payload, to_json_safe


router = APIRouter(prefix="/demo-mode", tags=["Client Demo Mode"])
demo_mode_service = ClientDemoService()


@router.get("/status")
async def get_demo_mode_status() -> JSONResponse:
    try:
        return JSONResponse(content=to_json_safe(demo_mode_service.get_status()))
    except Exception as exc:
        return JSONResponse(content=safe_error_payload(f"Demo mode status unavailable: {exc}", "demo_mode"))


@router.get("/overview")
async def get_demo_mode_overview() -> JSONResponse:
    try:
        return JSONResponse(content=to_json_safe(demo_mode_service.get_overview()))
    except Exception as exc:
        return JSONResponse(content=safe_error_payload(f"Demo mode overview unavailable: {exc}", "demo_mode"))


@router.get("/kpis")
async def get_demo_mode_kpis() -> JSONResponse:
    try:
        return JSONResponse(content=to_json_safe(demo_mode_service.get_kpis()))
    except Exception:
        return JSONResponse(content=[])


@router.get("/pipeline-summary")
async def get_demo_mode_pipeline_summary() -> JSONResponse:
    try:
        return JSONResponse(content=to_json_safe(demo_mode_service.get_pipeline_summary()))
    except Exception as exc:
        return JSONResponse(content=safe_error_payload(f"Demo mode pipeline summary unavailable: {exc}", "demo_mode"))
