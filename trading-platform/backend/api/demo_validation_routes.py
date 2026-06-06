from fastapi import APIRouter, Query

from backend.demo_validation.e2e_demo_validation_service import E2EDemoValidationService
from backend.demo_validation.eurusd_demo_validation_service import EURUSDDemoValidationService
from backend.demo_validation.nifty50_demo_validation_service import NIFTY50DemoValidationService
from backend.demo_validation.xauusd_demo_validation_service import XAUUSDDemoValidationService


router = APIRouter(prefix="/demo-validation", tags=["Demo Validation"])


@router.get("/e2e/status")
async def get_e2e_demo_validation_status() -> dict:
    service = E2EDemoValidationService()
    try:
        return service.status()
    finally:
        service.close()


@router.post("/e2e/run")
async def run_e2e_demo_validation() -> dict:
    service = E2EDemoValidationService()
    try:
        return service.run_validation()
    finally:
        service.close()


@router.get("/e2e/latest")
async def get_latest_e2e_demo_validation() -> dict:
    service = E2EDemoValidationService()
    try:
        return service.latest()
    finally:
        service.close()


@router.get("/e2e/history")
async def get_e2e_demo_validation_history(limit: int = Query(default=50, ge=1, le=500)) -> list[dict]:
    service = E2EDemoValidationService()
    try:
        return service.history(limit)
    finally:
        service.close()


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


@router.get("/eurusd/status")
async def get_eurusd_demo_validation_status() -> dict:
    service = EURUSDDemoValidationService()
    try:
        return service.status()
    finally:
        service.close()


@router.post("/eurusd/run")
async def run_eurusd_demo_validation() -> dict:
    service = EURUSDDemoValidationService()
    try:
        return service.run_validation()
    finally:
        service.close()


@router.get("/eurusd/latest")
async def get_latest_eurusd_demo_validation() -> dict:
    service = EURUSDDemoValidationService()
    try:
        return service.latest()
    finally:
        service.close()


@router.get("/eurusd/history")
async def get_eurusd_demo_validation_history(limit: int = Query(default=50, ge=1, le=500)) -> list[dict]:
    service = EURUSDDemoValidationService()
    try:
        return service.history(limit)
    finally:
        service.close()


@router.get("/nifty50/status")
async def get_nifty50_demo_validation_status() -> dict:
    service = NIFTY50DemoValidationService()
    try:
        return service.status()
    finally:
        service.close()


@router.post("/nifty50/run")
async def run_nifty50_demo_validation() -> dict:
    service = NIFTY50DemoValidationService()
    try:
        return service.run_validation()
    finally:
        service.close()


@router.get("/nifty50/latest")
async def get_latest_nifty50_demo_validation() -> dict:
    service = NIFTY50DemoValidationService()
    try:
        return service.latest()
    finally:
        service.close()


@router.get("/nifty50/history")
async def get_nifty50_demo_validation_history(limit: int = Query(default=50, ge=1, le=500)) -> list[dict]:
    service = NIFTY50DemoValidationService()
    try:
        return service.history(limit)
    finally:
        service.close()
