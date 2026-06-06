from fastapi import APIRouter, Query

from backend.demo_validation.xauusd_demo_validation_service import XAUUSDDemoValidationService


router = APIRouter(prefix="/demo-validation", tags=["Demo Validation"])


@router.get("/xauusd/status")
async def get_xauusd_demo_validation_status() -> dict:
    service = XAUUSDDemoValidationService()
    try:
        return service.status()
    finally:
        service.close()


@router.post("/xauusd/run")
async def run_xauusd_demo_validation() -> dict:
    service = XAUUSDDemoValidationService()
    try:
        return service.run_validation()
    finally:
        service.close()


@router.get("/xauusd/latest")
async def get_latest_xauusd_demo_validation() -> dict:
    service = XAUUSDDemoValidationService()
    try:
        return service.latest()
    finally:
        service.close()


@router.get("/xauusd/history")
async def get_xauusd_demo_validation_history(limit: int = Query(default=50, ge=1, le=500)) -> list[dict]:
    service = XAUUSDDemoValidationService()
    try:
        return service.history(limit)
    finally:
        service.close()
