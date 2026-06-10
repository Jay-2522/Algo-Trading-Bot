from typing import Any

from fastapi import APIRouter, Body

from backend.api.client_signal_engine_routes import client_signal_engine
from backend.api.mt5_demo_routes import vantage_xauusd_demo_validation_service
from backend.execution_mode.execution_mode_service import ExecutionModeService


router = APIRouter(prefix="/execution-mode", tags=["Execution Mode"])
execution_mode_service = ExecutionModeService(
    signal_provider=client_signal_engine,
    guarded_execution_service=vantage_xauusd_demo_validation_service,
)
client_signal_engine.execution_mode_service = execution_mode_service


@router.get("/status")
async def get_execution_mode_status() -> dict:
    return execution_mode_service.status()


@router.post("/set")
async def set_execution_mode(payload: dict[str, Any] = Body(default_factory=dict)) -> dict:
    return execution_mode_service.set_config(payload)


@router.post("/approve-signal")
async def approve_execution_mode_signal(payload: dict[str, Any] = Body(default_factory=dict)) -> dict:
    return execution_mode_service.approve_signal(payload)


@router.post("/reject-signal")
async def reject_execution_mode_signal(payload: dict[str, Any] = Body(default_factory=dict)) -> dict:
    return execution_mode_service.reject_signal(payload)


@router.get("/pending-approvals")
async def get_execution_mode_pending_approvals() -> list[dict]:
    return execution_mode_service.pending_approvals()


@router.get("/history")
async def get_execution_mode_history(limit: int = 100) -> list[dict]:
    return execution_mode_service.history(limit)
