from fastapi import APIRouter, HTTPException

from backend.risk_engine.risk_config import get_default_risk_config
from backend.risk_engine.risk_models import (
    KillSwitchActivationRequest,
    PositionSizeRequest,
    PositionSizeResponse,
    RiskCheckRequest,
    RiskCheckResponse,
    RiskConfig,
    RiskStatus,
)
from backend.risk_engine.risk_service import get_risk_service


router = APIRouter(prefix="/risk", tags=["Risk Management"])
risk_service = get_risk_service()


@router.get("/status", response_model=RiskStatus)
async def get_risk_status() -> RiskStatus:
    return risk_service.get_risk_status()


@router.get("/config", response_model=RiskConfig)
async def get_risk_config() -> RiskConfig:
    return get_default_risk_config()


@router.post("/calculate-position-size", response_model=PositionSizeResponse)
async def calculate_position_size(request: PositionSizeRequest) -> PositionSizeResponse:
    try:
        return risk_service.calculate_position_size(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/check-trade", response_model=RiskCheckResponse)
async def check_trade(request: RiskCheckRequest) -> RiskCheckResponse:
    try:
        return risk_service.evaluate_trade_permission(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/kill-switch/activate")
async def activate_kill_switch(request: KillSwitchActivationRequest) -> dict:
    try:
        return {
            "status": "activated",
            "kill_switch": risk_service.activate_kill_switch(request.reason),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/kill-switch/deactivate")
async def deactivate_kill_switch() -> dict:
    return {
        "status": "deactivated",
        "kill_switch": risk_service.deactivate_kill_switch(),
    }
