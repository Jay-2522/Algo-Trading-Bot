from fastapi import APIRouter

from backend.phase3_readiness.phase3_readiness_models import (
    Phase3ModuleStatus,
    Phase3PipelineValidation,
    Phase3ReadinessReport,
    Phase3SafetyAudit,
)
from backend.phase3_readiness.phase3_readiness_service import Phase3ReadinessService


router = APIRouter(prefix="/phase3", tags=["Phase 3 Readiness"])
phase3_readiness_service = Phase3ReadinessService()


@router.get("/status", response_model=Phase3ReadinessReport)
async def get_phase3_status() -> Phase3ReadinessReport:
    return phase3_readiness_service.get_status()


@router.get("/modules", response_model=list[Phase3ModuleStatus])
async def get_phase3_modules() -> list[Phase3ModuleStatus]:
    return phase3_readiness_service.get_modules()


@router.get("/routes")
async def get_phase3_routes() -> dict:
    return phase3_readiness_service.get_routes()


@router.get("/pipeline", response_model=Phase3PipelineValidation)
async def get_phase3_pipeline() -> Phase3PipelineValidation:
    return phase3_readiness_service.validate_pipeline()


@router.get("/safety-audit", response_model=Phase3SafetyAudit)
async def get_phase3_safety_audit() -> Phase3SafetyAudit:
    return phase3_readiness_service.run_safety_audit()


@router.get("/client-readiness")
async def get_phase3_client_readiness() -> dict:
    return phase3_readiness_service.get_client_readiness_report()
