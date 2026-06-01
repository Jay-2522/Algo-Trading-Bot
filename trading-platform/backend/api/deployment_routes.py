from fastapi import APIRouter

from backend.deployment.deployment_models import DeploymentReadinessStatus
from backend.deployment.deployment_readiness_service import DeploymentReadinessService


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
