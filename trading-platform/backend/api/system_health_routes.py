from fastapi import APIRouter, Request

from backend.config.settings import get_settings
from backend.system_health.health_models import PhaseCompletionReport, RouteAuditResult, SafetyScanResult, SystemReadiness
from backend.system_health.system_health_service import SystemHealthService


router = APIRouter(prefix="/system", tags=["System Health & Phase 1 Hardening"])


def _service(request: Request) -> SystemHealthService:
    return SystemHealthService(request.app)


@router.get("/status")
async def get_system_status(request: Request) -> dict:
    return _service(request).get_system_status()


@router.get("/readiness", response_model=SystemReadiness)
async def get_readiness(request: Request) -> SystemReadiness:
    return _service(request).get_readiness()


@router.get("/safety-scan", response_model=SafetyScanResult)
async def run_safety_scan(request: Request) -> SafetyScanResult:
    return _service(request).run_safety_scan()


@router.get("/routes", response_model=RouteAuditResult)
async def audit_routes(request: Request) -> RouteAuditResult:
    return _service(request).audit_routes()


@router.get("/phase-report", response_model=PhaseCompletionReport)
async def get_phase_report(request: Request) -> PhaseCompletionReport:
    return _service(request).get_phase_report()


@router.get("/config-summary")
async def get_config_summary() -> dict:
    settings = get_settings()
    database_mode = "sqlite" if settings.database_url.startswith("sqlite") else "configured_external_database"
    return {
        "environment": settings.environment,
        "simulation_only": True,
        "live_execution_enabled": False,
        "database_mode": database_mode,
        "mt5_mode": "READ_ONLY_DISABLED_FOR_ORDER_PLACEMENT",
        "streaming_mode": "SIMULATION_OR_MT5_READ_ONLY",
        "loop_mode": "SIMULATION_ONLY",
    }
