from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from backend.demo_execution.demo_execution_models import DemoExecutionResult
from backend.execution_confirmation.confirmation_tracker import ExecutionConfirmationTracker
from backend.strategy_execution_bridge.demo_approval_models import DemoExecutionApprovalRequest
from backend.strategy_execution_bridge.demo_execution_approval_service import DemoExecutionApprovalService
from backend.strategy_execution_bridge.end_to_end_flow_store import EndToEndFlowStore
from backend.strategy_execution_bridge.final_demo_execution_models import FinalDemoExecutionRequest
from backend.strategy_execution_bridge.final_demo_execution_service import FinalDemoExecutionService
from backend.strategy_execution_bridge.strategy_execution_bridge_service import StrategyExecutionBridgeService


FinalStatus = Literal[
    "COMPLETED_DEMO_FILLED",
    "COMPLETED_DEMO_REJECTED",
    "COMPLETED_MT5_UNAVAILABLE",
    "BLOCKED_AT_BRIDGE",
    "BLOCKED_AT_RISK",
    "BLOCKED_AT_APPROVAL",
    "BLOCKED_AT_FINAL_CONFIRMATION",
    "FAILED_SAFE",
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EndToEndDemoFlowResult(BaseModel):
    flow_id: str = Field(default_factory=lambda: f"e2e_demo_flow_{uuid4().hex[:12]}")
    source_signal_id: str | None = None
    symbol: str | None = None
    action: str | None = None
    confidence: float = 0.0
    bridge_decision_id: str | None = None
    intent_id: str | None = None
    risk_decision_id: str | None = None
    queue_preview_id: str | None = None
    approval_id: str | None = None
    candidate_id: str | None = None
    final_execution_id: str | None = None
    demo_execution_result_id: str | None = None
    confirmation_id: str | None = None
    final_status: FinalStatus = "FAILED_SAFE"
    completed_steps: list[str] = Field(default_factory=list)
    failed_step: str | None = None
    rejection_reasons: list[str] = Field(default_factory=list)
    mt5_retcode: int | str | None = None
    mt5_order: int | str | None = None
    mt5_deal: int | str | None = None
    simulation_only: bool = True
    demo_execution: bool = True
    live_execution_enabled: bool = False
    broker_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)

    def model_post_init(self, __context: Any) -> None:
        self.simulation_only = True
        self.demo_execution = True
        self.live_execution_enabled = False
        self.broker_execution_enabled = False


class EndToEndDemoFlowService:
    """Run the complete strategy-to-guarded-demo pipeline with every guard intact."""

    def __init__(
        self,
        bridge_service: StrategyExecutionBridgeService | None = None,
        approval_service: DemoExecutionApprovalService | None = None,
        final_execution_service: FinalDemoExecutionService | None = None,
        confirmation_tracker: ExecutionConfirmationTracker | None = None,
        store: EndToEndFlowStore | None = None,
    ) -> None:
        self.bridge_service = bridge_service or StrategyExecutionBridgeService()
        self.approval_service = approval_service or DemoExecutionApprovalService()
        self.final_execution_service = final_execution_service or FinalDemoExecutionService()
        self.confirmation_tracker = confirmation_tracker or ExecutionConfirmationTracker()
        self.store = store or EndToEndFlowStore()

    def get_status(self) -> dict[str, Any]:
        return {
            "status": "OPERATIONAL",
            "mode": "END_TO_END_STRATEGY_TO_GUARDED_DEMO_EXECUTION_VERIFIER",
            "steps": [
                "strategy_signal",
                "bridge_validation",
                "execution_intent",
                "risk_evaluation",
                "queue_preview",
                "demo_approval",
                "demo_candidate",
                "final_execution_confirmation",
                "guarded_mt5_demo_executor",
                "execution_result",
                "confirmation_tracking",
                "audit_trail",
            ],
            "final_confirmation_required": True,
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def run_mock_eurusd_demo_flow(self) -> EndToEndDemoFlowResult:
        return self.run_from_signal(self._mock_eurusd_signal())

    def run_from_signal(self, signal: dict[str, Any] | Any) -> EndToEndDemoFlowResult:
        result = self._base_result(signal)
        try:
            bridge_decision = self.bridge_service.evaluate_and_preview_signal(signal)
            result.bridge_decision_id = bridge_decision.decision_id
            result.risk_decision_id = bridge_decision.risk_decision_id
            result.queue_preview_id = bridge_decision.queue_preview_id
            if bridge_decision.mapped_intent is not None:
                result.intent_id = bridge_decision.mapped_intent.intent_id
            result.completed_steps.append("bridge_validation")

            if not bridge_decision.eligible:
                failed_status = "BLOCKED_AT_RISK" if bridge_decision.bridge_status == "REJECTED_RISK_ENGINE" else "BLOCKED_AT_BRIDGE"
                return self._store_failed(
                    result,
                    failed_status,
                    "risk_evaluation" if failed_status == "BLOCKED_AT_RISK" else "bridge_validation",
                    bridge_decision.rejection_reasons,
                )
            if not bridge_decision.queue_preview_created:
                return self._store_failed(result, "BLOCKED_AT_BRIDGE", "queue_preview", ["Queue preview was not created."])
            result.completed_steps.extend(["execution_intent", "risk_evaluation", "queue_preview"])

            approval = self.approval_service.approve_decision(
                DemoExecutionApprovalRequest(
                    decision_id=bridge_decision.decision_id,
                    confirm_demo_approval=True,
                    requested_by="phase9_day5_e2e",
                    reason="End-to-end demo flow verification approval.",
                )
            )
            result.approval_id = approval.approval_id
            result.candidate_id = approval.demo_execution_candidate_id
            if not approval.approved or not approval.demo_execution_candidate_id:
                return self._store_failed(result, "BLOCKED_AT_APPROVAL", "demo_approval", approval.rejection_reasons)
            result.completed_steps.extend(["demo_approval", "demo_candidate"])

            final_decision = self.final_execution_service.execute_candidate(
                FinalDemoExecutionRequest(
                    candidate_id=approval.demo_execution_candidate_id,
                    confirm_demo_execution=True,
                    requested_by="phase9_day5_e2e",
                    reason="End-to-end final demo execution confirmation.",
                )
            )
            result.final_execution_id = final_decision.final_execution_id
            result.demo_execution_result_id = final_decision.demo_execution_result_id
            result.mt5_retcode = final_decision.mt5_retcode
            result.mt5_order = final_decision.mt5_order
            result.mt5_deal = final_decision.mt5_deal
            result.completed_steps.append("final_execution_confirmation")

            final_status = self._map_final_status(final_decision.execution_status)
            if final_status == "BLOCKED_AT_FINAL_CONFIRMATION":
                return self._store_failed(
                    result,
                    final_status,
                    "guarded_mt5_demo_executor",
                    final_decision.rejection_reasons,
                )
            if final_status == "FAILED_SAFE":
                return self._store_failed(result, final_status, "guarded_mt5_demo_executor", final_decision.rejection_reasons)

            result.completed_steps.extend(["guarded_mt5_demo_executor", "execution_result"])
            confirmation = self._track_confirmation(final_decision)
            if confirmation is not None:
                result.confirmation_id = confirmation.execution_id
                result.completed_steps.append("confirmation_tracking")
            result.completed_steps.append("audit_trail")
            result.final_status = final_status
            result.rejection_reasons = list(final_decision.rejection_reasons)
            return self.store.store_flow(result)
        except Exception as exc:
            return self._store_failed(result, "FAILED_SAFE", "end_to_end_flow", [f"End-to-end demo flow failed safe: {exc}"])

    def list_flows(self, limit: int = 100):
        return self.store.list_flows(limit)

    def get_flow(self, flow_id: str):
        return self.store.get_flow(flow_id)

    def close(self) -> None:
        self.bridge_service.close()

    def _track_confirmation(self, final_decision: Any):
        if not final_decision.demo_execution_result_id:
            return None
        demo_result = DemoExecutionResult(
            execution_id=final_decision.demo_execution_result_id,
            queue_id=final_decision.queue_preview_id or final_decision.candidate_id,
            broker_id=FinalDemoExecutionService.DEFAULT_BROKER_ID,
            account_id=FinalDemoExecutionService.DEFAULT_ACCOUNT_ID,
            canonical_symbol=final_decision.symbol,
            broker_symbol=final_decision.symbol,
            action=final_decision.action,
            requested_lot=final_decision.lot,
            status=self._demo_result_status(final_decision.execution_status),
            rejection_reasons=list(final_decision.rejection_reasons),
            mt5_retcode=final_decision.mt5_retcode,
            mt5_order=final_decision.mt5_order,
            mt5_deal=final_decision.mt5_deal,
            demo_execution=True,
            simulation_only=True,
            live_execution_enabled=False,
            broker_execution_enabled=False,
        )
        return self.confirmation_tracker.track_execution(demo_result)

    def _demo_result_status(self, status: str) -> str:
        if status in {"DEMO_FILLED", "DEMO_REJECTED", "MT5_UNAVAILABLE", "FAILED_SAFE"}:
            return status
        return "BLOCKED"

    def _map_final_status(self, status: str) -> FinalStatus:
        if status == "DEMO_FILLED":
            return "COMPLETED_DEMO_FILLED"
        if status == "DEMO_REJECTED":
            return "COMPLETED_DEMO_REJECTED"
        if status == "MT5_UNAVAILABLE":
            return "COMPLETED_MT5_UNAVAILABLE"
        if status == "FAILED_SAFE":
            return "FAILED_SAFE"
        return "BLOCKED_AT_FINAL_CONFIRMATION"

    def _store_failed(
        self,
        result: EndToEndDemoFlowResult,
        status: FinalStatus,
        failed_step: str,
        reasons: list[str],
    ) -> EndToEndDemoFlowResult:
        result.final_status = status
        result.failed_step = failed_step
        result.rejection_reasons = list(reasons)
        return self.store.store_flow(result)

    def _base_result(self, signal: dict[str, Any] | Any) -> EndToEndDemoFlowResult:
        return EndToEndDemoFlowResult(
            source_signal_id=str(self._get(signal, "signal_id", "manual-signal")),
            symbol=str(self._get(signal, "symbol", "UNKNOWN")).upper(),
            action=str(self._get(signal, "action", "WAIT")).upper(),
            confidence=float(self._get(signal, "confidence", 0.0) or 0.0),
            completed_steps=["strategy_signal"],
            simulation_only=True,
            demo_execution=True,
            live_execution_enabled=False,
            broker_execution_enabled=False,
        )

    def _mock_eurusd_signal(self) -> dict[str, Any]:
        return {
            "signal_id": f"mock_eurusd_e2e_{uuid4().hex[:8]}",
            "symbol": "EURUSD",
            "action": "BUY",
            "confidence": 85,
            "execution_allowed": True,
            "trade_quality": "A",
            "risk_mode": "NORMAL",
            "reason": "Phase 9 Day 5 mock EURUSD demo flow.",
            "suggested_lot": 0.01,
            "metadata": {
                "phase": "PHASE_9_DAY_5_E2E",
                "simulation_only": True,
                "live_execution_enabled": False,
                "broker_execution_enabled": False,
            },
            "news_context": {"high_impact_event_active": False, "trade_action": "ALLOW", "risk_level": "LOW"},
            "regime_context": {"risk_mode": "NORMAL"},
        }

    def _get(self, obj: Any | None, key: str, default: Any) -> Any:
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)
