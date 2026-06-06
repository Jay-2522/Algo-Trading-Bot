from fastapi import APIRouter

from backend.demo_environment.demo_environment_service import DemoEnvironmentService


router = APIRouter(prefix="/demo-environment", tags=["Demo Environment"])
service = DemoEnvironmentService()


@router.get("/status")
async def get_demo_environment_status() -> dict:
    return service.get_status()


@router.get("/readiness")
async def get_demo_environment_readiness() -> dict:
    return service.get_readiness()


@router.get("/checklist")
async def get_demo_environment_checklist() -> dict:
    return service.get_checklist()
