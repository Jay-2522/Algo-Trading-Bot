from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.operational_intelligence.operational_intelligence_service import OperationalIntelligenceService
from backend.utils.json_safety import safe_error_payload, to_json_safe


router = APIRouter(prefix="/operational-intelligence", tags=["Operational Intelligence"])
operational_intelligence_service = OperationalIntelligenceService()


@router.get("/status")
async def get_operational_intelligence_status() -> JSONResponse:
    try:
        return JSONResponse(content=to_json_safe(operational_intelligence_service.get_status()))
    except Exception as exc:
        return JSONResponse(content=safe_error_payload(f"Operational intelligence status unavailable: {exc}", "operational_intelligence"))


@router.get("/health-summary")
async def get_operational_health_summary() -> JSONResponse:
    try:
        return JSONResponse(content=to_json_safe(operational_intelligence_service.get_health_summary()))
    except Exception as exc:
        return JSONResponse(content=safe_error_payload(f"Operational health summary unavailable: {exc}", "operational_intelligence"))


@router.get("/modules")
async def get_operational_modules() -> JSONResponse:
    try:
        return JSONResponse(content=to_json_safe(operational_intelligence_service.get_modules()))
    except Exception:
        return JSONResponse(content=[])


@router.get("/warnings")
async def get_operational_warnings() -> JSONResponse:
    try:
        return JSONResponse(content=to_json_safe(operational_intelligence_service.get_warnings()))
    except Exception:
        return JSONResponse(content=[])


@router.get("/health-score")
async def get_operational_health_score() -> JSONResponse:
    try:
        return JSONResponse(content=to_json_safe(operational_intelligence_service.get_health_score()))
    except Exception as exc:
        return JSONResponse(content=safe_error_payload(f"Operational health score unavailable: {exc}", "operational_intelligence"))
