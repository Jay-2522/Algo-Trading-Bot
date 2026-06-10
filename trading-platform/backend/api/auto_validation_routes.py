from typing import Any

from fastapi import APIRouter, Body

from backend.api.client_signal_engine_routes import client_signal_engine
from backend.api.mt5_demo_routes import mt5_position_monitoring_service, service as mt5_demo_service, vantage_xauusd_demo_validation_service
from backend.api.trade_journal_persistence_routes import persistent_trade_journal_service
from backend.auto_validation.auto_validation_service import AutoValidationService


router = APIRouter(prefix="/auto-validation", tags=["AUTO Demo Validation"])
auto_validation_service = AutoValidationService(
    signal_provider=client_signal_engine,
    guarded_execution_service=vantage_xauusd_demo_validation_service,
    journal_service=persistent_trade_journal_service,
    position_service=mt5_position_monitoring_service,
    mt5_demo_service=mt5_demo_service,
)


@router.get("/status")
async def get_auto_validation_status() -> dict:
    return auto_validation_service.status()


@router.post("/start")
async def start_auto_validation(payload: dict[str, Any] = Body(default_factory=dict)) -> dict:
    return auto_validation_service.start(payload)


@router.post("/pause")
async def pause_auto_validation() -> dict:
    return auto_validation_service.pause()


@router.post("/resume")
async def resume_auto_validation() -> dict:
    return auto_validation_service.resume()


@router.post("/stop")
async def stop_auto_validation(payload: dict[str, Any] = Body(default_factory=dict)) -> dict:
    return auto_validation_service.stop(str(payload.get("reason") or "Stopped manually."))


@router.post("/emergency-stop")
async def emergency_stop_auto_validation() -> dict:
    return auto_validation_service.emergency_stop()


@router.get("/trades")
async def get_auto_validation_trades() -> list[dict]:
    return auto_validation_service.trades()


@router.get("/summary")
async def get_auto_validation_summary() -> dict:
    return auto_validation_service.summary()


@router.get("/events")
async def get_auto_validation_events(limit: int = 100) -> list[dict]:
    return auto_validation_service.events[-max(1, min(limit, 500)) :]
