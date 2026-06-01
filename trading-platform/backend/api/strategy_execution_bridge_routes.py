from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query

from backend.strategy_execution_bridge.bridge_models import StrategyBridgeDecision
from backend.strategy_execution_bridge.demo_approval_models import (
    DemoExecutionApprovalDecision,
    DemoExecutionApprovalRequest,
    DemoExecutionCandidate,
)
from backend.strategy_execution_bridge.demo_execution_approval_service import DemoExecutionApprovalService
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


@router.get("/demo-approval/status")
async def get_demo_approval_status() -> dict[str, Any]:
    return DemoExecutionApprovalService().get_status()


@router.post("/demo-approval/approve", response_model=DemoExecutionApprovalDecision)
async def approve_demo_execution_candidate(payload: DemoExecutionApprovalRequest) -> DemoExecutionApprovalDecision:
    return DemoExecutionApprovalService().approve_decision(payload)


@router.get("/demo-approval/approvals", response_model=list[DemoExecutionApprovalDecision])
async def list_demo_approvals(limit: int = Query(default=100, ge=1, le=1000)) -> list[DemoExecutionApprovalDecision]:
    return DemoExecutionApprovalService().list_approvals(limit)


@router.get("/demo-approval/history", response_model=list[DemoExecutionApprovalDecision])
async def list_demo_approval_history(limit: int = Query(default=100, ge=1, le=1000)) -> list[DemoExecutionApprovalDecision]:
    return DemoExecutionApprovalService().list_approvals(limit)


@router.get("/demo-approval/candidates", response_model=list[DemoExecutionCandidate])
async def list_demo_candidates(limit: int = Query(default=100, ge=1, le=1000)) -> list[DemoExecutionCandidate]:
    return DemoExecutionApprovalService().list_candidates(limit)


@router.get("/demo-approval/approvals/{approval_id}", response_model=DemoExecutionApprovalDecision)
async def get_demo_approval(approval_id: str) -> DemoExecutionApprovalDecision:
    approval = DemoExecutionApprovalService().get_approval(approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="Demo execution approval not found.")
    return approval


@router.get("/demo-approval/candidates/{candidate_id}", response_model=DemoExecutionCandidate)
async def get_demo_candidate(candidate_id: str) -> DemoExecutionCandidate:
    candidate = DemoExecutionApprovalService().get_candidate(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Demo execution candidate not found.")
    return candidate
