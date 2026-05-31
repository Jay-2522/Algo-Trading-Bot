from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query

from backend.strategy_execution_bridge.bridge_models import StrategyBridgeDecision
from backend.strategy_execution_bridge.strategy_execution_bridge_service import StrategyExecutionBridgeService


router = APIRouter(prefix="/strategy-execution-bridge", tags=["Strategy Execution Bridge"])


@router.get("/status")
async def get_strategy_execution_bridge_status() -> dict[str, Any]:
    service = StrategyExecutionBridgeService()
    try:
        return service.get_status()
    finally:
        service.close()


@router.post("/evaluate-signal", response_model=StrategyBridgeDecision)
async def evaluate_strategy_signal(payload: dict[str, Any] = Body(default_factory=dict)) -> StrategyBridgeDecision:
    service = StrategyExecutionBridgeService()
    try:
        return service.evaluate_signal(payload)
    finally:
        service.close()


@router.post("/preview-signal", response_model=StrategyBridgeDecision)
async def preview_strategy_signal(payload: dict[str, Any] = Body(default_factory=dict)) -> StrategyBridgeDecision:
    service = StrategyExecutionBridgeService()
    try:
        return service.create_queue_preview_from_signal(payload)
    finally:
        service.close()


@router.post("/evaluate-and-preview", response_model=StrategyBridgeDecision)
async def evaluate_and_preview_strategy_signal(payload: dict[str, Any] = Body(default_factory=dict)) -> StrategyBridgeDecision:
    service = StrategyExecutionBridgeService()
    try:
        return service.evaluate_and_preview_signal(payload)
    finally:
        service.close()


@router.post("/xauusd/latest", response_model=StrategyBridgeDecision)
async def bridge_latest_xauusd_signal() -> StrategyBridgeDecision:
    service = StrategyExecutionBridgeService()
    try:
        return service.bridge_latest_xauusd_signal()
    finally:
        service.close()


@router.post("/eurusd/latest", response_model=StrategyBridgeDecision)
async def bridge_latest_eurusd_signal() -> StrategyBridgeDecision:
    service = StrategyExecutionBridgeService()
    try:
        return service.bridge_latest_eurusd_signal()
    finally:
        service.close()


@router.get("/decisions", response_model=list[StrategyBridgeDecision])
async def list_bridge_decisions(limit: int = Query(default=100, ge=1, le=1000)) -> list[StrategyBridgeDecision]:
    service = StrategyExecutionBridgeService()
    try:
        return service.list_decisions(limit)
    finally:
        service.close()


@router.get("/decisions/{decision_id}", response_model=StrategyBridgeDecision)
async def get_bridge_decision(decision_id: str) -> StrategyBridgeDecision:
    service = StrategyExecutionBridgeService()
    try:
        decision = service.get_decision(decision_id)
        if decision is None:
            raise HTTPException(status_code=404, detail="Strategy bridge decision not found.")
        return decision
    finally:
        service.close()
