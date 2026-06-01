from fastapi import APIRouter

from backend.deployment.deployment_models import DeploymentReadinessStatus
from backend.deployment.deployment_readiness_service import DeploymentReadinessService
from backend.deployment.runtime_manager import RuntimeManager
from backend.deployment.runtime_models import RuntimeServiceStatus, VPSRuntimeStatus


router = APIRouter(prefix="/deployment", tags=["Deployment Readiness"])


@router.get("/status", response_model=DeploymentReadinessStatus)
async def get_deployment_status() -> DeploymentReadinessStatus:
    return DeploymentReadinessService().get_status()


@router.get("/readiness", response_model=DeploymentReadinessStatus)
async def get_deployment_readiness() -> DeploymentReadinessStatus:
    return DeploymentReadinessService().run_full_check()


@router.get("/checklist")
async def get_deployment_checklist() -> dict:
    return DeploymentReadinessService().get_checklist()


@router.get("/blockers")
async def get_deployment_blockers() -> dict:
    return DeploymentReadinessService().get_blockers()


@router.get("/warnings")
async def get_deployment_warnings() -> dict:
    return DeploymentReadinessService().get_warnings()


@router.get("/runtime/status", response_model=VPSRuntimeStatus)
async def get_runtime_status() -> VPSRuntimeStatus:
    return RuntimeManager().get_runtime_status()


@router.get("/runtime/backend", response_model=RuntimeServiceStatus)
async def get_runtime_backend_status() -> RuntimeServiceStatus:
    return RuntimeManager().get_backend_status()


@router.get("/runtime/frontend", response_model=RuntimeServiceStatus)
async def get_runtime_frontend_status() -> RuntimeServiceStatus:
    return RuntimeManager().get_frontend_status()


@router.get("/runtime/healthcheck")
async def get_runtime_healthcheck() -> dict:
    return RuntimeManager().health_checker.check_all()


@router.get("/runtime/mt5-notes")
async def get_runtime_mt5_notes() -> dict:
    return RuntimeManager().get_mt5_runtime_notes()


@router.get("/runtime/audit-events")
async def get_runtime_audit_events(limit: int = 100) -> list[dict]:
    return RuntimeManager().list_audit_events(limit)
