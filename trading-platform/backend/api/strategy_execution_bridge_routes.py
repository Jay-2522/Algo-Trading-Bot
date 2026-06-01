from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query

from backend.strategy_execution_bridge.bridge_models import StrategyBridgeDecision
from backend.strategy_execution_bridge.demo_approval_models import (
    DemoExecutionApprovalDecision,
    DemoExecutionApprovalRequest,
    DemoExecutionCandidate,
)
from backend.strategy_execution_bridge.demo_execution_approval_service import DemoExecutionApprovalService
from backend.strategy_execution_bridge.end_to_end_demo_flow import EndToEndDemoFlowResult, EndToEndDemoFlowService
from backend.strategy_execution_bridge.execution_operations_center import ExecutionOperationsCenter
from backend.strategy_execution_bridge.execution_operations_models import ExecutionOperationsOverview, ExecutionPipelineEvent
from backend.strategy_execution_bridge.final_demo_execution_models import (
    FinalDemoExecutionDecision,
    FinalDemoExecutionRequest,
)
from backend.strategy_execution_bridge.final_demo_execution_service import FinalDemoExecutionService
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


@router.get("/final-demo-execution/status")
async def get_final_demo_execution_status() -> dict[str, Any]:
    return FinalDemoExecutionService().get_status()


@router.post("/final-demo-execution/execute", response_model=FinalDemoExecutionDecision)
async def execute_final_demo_candidate(payload: FinalDemoExecutionRequest) -> FinalDemoExecutionDecision:
    return FinalDemoExecutionService().execute_candidate(payload)


@router.get("/final-demo-execution/executions", response_model=list[FinalDemoExecutionDecision])
async def list_final_demo_executions(limit: int = Query(default=100, ge=1, le=1000)) -> list[FinalDemoExecutionDecision]:
    return FinalDemoExecutionService().list_executions(limit)


@router.get("/final-demo-execution/executions/{final_execution_id}", response_model=FinalDemoExecutionDecision)
async def get_final_demo_execution(final_execution_id: str) -> FinalDemoExecutionDecision:
    execution = FinalDemoExecutionService().get_execution(final_execution_id)
    if execution is None:
        raise HTTPException(status_code=404, detail="Final demo execution decision not found.")
    return execution


@router.get("/e2e/status")
async def get_end_to_end_demo_flow_status() -> dict[str, Any]:
    service = EndToEndDemoFlowService()
    try:
        return service.get_status()
    finally:
        service.close()


@router.post("/e2e/mock-eurusd-demo", response_model=EndToEndDemoFlowResult)
async def run_mock_eurusd_end_to_end_demo_flow() -> EndToEndDemoFlowResult:
    service = EndToEndDemoFlowService()
    try:
        return service.run_mock_eurusd_demo_flow()
    finally:
        service.close()


@router.post("/e2e/run-signal", response_model=EndToEndDemoFlowResult)
async def run_signal_end_to_end_demo_flow(payload: dict[str, Any] = Body(default_factory=dict)) -> EndToEndDemoFlowResult:
    service = EndToEndDemoFlowService()
    try:
        return service.run_from_signal(payload)
    finally:
        service.close()


@router.get("/e2e/flows", response_model=list[EndToEndDemoFlowResult])
async def list_end_to_end_demo_flows(limit: int = Query(default=100, ge=1, le=1000)) -> list[EndToEndDemoFlowResult]:
    service = EndToEndDemoFlowService()
    try:
        return service.list_flows(limit)
    finally:
        service.close()


@router.get("/e2e/flows/{flow_id}", response_model=EndToEndDemoFlowResult)
async def get_end_to_end_demo_flow(flow_id: str) -> EndToEndDemoFlowResult:
    service = EndToEndDemoFlowService()
    try:
        flow = service.get_flow(flow_id)
        if flow is None:
            raise HTTPException(status_code=404, detail="End-to-end demo flow not found.")
        return flow
    finally:
        service.close()


@router.get("/operations/status")
async def get_execution_operations_status() -> dict[str, Any]:
    return ExecutionOperationsCenter().get_status()


@router.get("/operations/overview", response_model=ExecutionOperationsOverview)
async def get_execution_operations_overview() -> ExecutionOperationsOverview:
    return ExecutionOperationsCenter().get_overview()


@router.get("/operations/pipeline-events", response_model=list[ExecutionPipelineEvent])
async def get_execution_operations_pipeline_events(limit: int = Query(default=100, ge=1, le=1000)) -> list[ExecutionPipelineEvent]:
    return ExecutionOperationsCenter().get_pipeline_events(limit)


@router.get("/operations/recent-executions")
async def get_execution_operations_recent_executions(limit: int = Query(default=100, ge=1, le=1000)) -> dict[str, Any]:
    return ExecutionOperationsCenter().get_recent_executions(limit)


@router.get("/operations/recent-rejections", response_model=list[ExecutionPipelineEvent])
async def get_execution_operations_recent_rejections(limit: int = Query(default=100, ge=1, le=1000)) -> list[ExecutionPipelineEvent]:
    return ExecutionOperationsCenter().get_recent_rejections(limit)


@router.get("/operations/readiness")
async def get_execution_operations_readiness() -> dict[str, Any]:
    return ExecutionOperationsCenter().get_readiness()


@router.get("/operations/health")
async def get_execution_operations_health() -> dict[str, Any]:
    center = ExecutionOperationsCenter()
    return {
        "health_score": center.get_health_score(),
        "status": center.get_overview().status,
        "pipeline_ready": center.get_overview().pipeline_ready,
        "simulation_only": True,
        "demo_execution": True,
        "live_execution_enabled": False,
        "broker_execution_enabled": False,
    }
