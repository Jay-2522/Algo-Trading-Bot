from typing import Any

from backend.demo_execution.demo_execution_models import DemoExecutionRequest
from backend.demo_execution.demo_execution_service import DemoExecutionService
from backend.execution_queue.execution_queue_models import ExecutionIntent, ExecutionQueueItem
from backend.execution_risk.execution_risk_evaluator import ExecutionRiskEvaluator
from backend.strategy_execution_bridge.demo_execution_approval_store import DemoExecutionApprovalStore
from backend.strategy_execution_bridge.final_demo_execution_guard import FinalDemoExecutionGuard
from backend.strategy_execution_bridge.final_demo_execution_models import (
    FinalDemoExecutionDecision,
    FinalDemoExecutionRequest,
)
from backend.strategy_execution_bridge.final_demo_execution_store import FinalDemoExecutionStore
from backend.trade_copier.copier_execution_bridge import CopierExecutionBridge


class FinalDemoExecutionService:
    """Handoff approved candidates to the existing guarded MT5 demo executor."""

    DEFAULT_ACCOUNT_ID = "STARTRADER_DEMO_1"
    DEFAULT_BROKER_ID = "STARTRADER"

    def __init__(
        self,
        approval_store: DemoExecutionApprovalStore | None = None,
        store: FinalDemoExecutionStore | None = None,
        guard: FinalDemoExecutionGuard | None = None,
        risk_evaluator: ExecutionRiskEvaluator | None = None,
        demo_execution_service: DemoExecutionService | None = None,
        copier_bridge: CopierExecutionBridge | None = None,
    ) -> None:
        self.approval_store = approval_store or DemoExecutionApprovalStore()
        self.store = store or FinalDemoExecutionStore()
        self.guard = guard or FinalDemoExecutionGuard()
        self.risk_evaluator = risk_evaluator or ExecutionRiskEvaluator()
        self.demo_execution_service = demo_execution_service or DemoExecutionService()
        self.copier_bridge = copier_bridge or CopierExecutionBridge()

    def get_status(self) -> dict[str, Any]:
        return {
            "status": "OPERATIONAL",
            "mode": "FINAL_GUARDED_MT5_DEMO_EXECUTION_HANDOFF",
            "guarded_demo_executor_only": True,
            "final_confirmation_required": True,
            "allowed_symbol": "EURUSD",
            "max_lot": 0.01,
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def execute_candidate(self, request: FinalDemoExecutionRequest | dict[str, Any]) -> FinalDemoExecutionDecision:
        request_model = request if isinstance(request, FinalDemoExecutionRequest) else FinalDemoExecutionRequest(**request)
        candidate = self.approval_store.get_candidate(request_model.candidate_id)
        try:
            allowed, status, reasons = self.guard.validate(
                candidate,
                request_model,
                already_executed=self.store.has_executed_candidate(request_model.candidate_id),
            )
            if not allowed:
                return self.store.store_decision(
                    self._decision(candidate, request_model, False, status, reasons)
                )

            risk_decision = self.risk_evaluator.evaluate_single_account_request(
                {
                    "request_id": request_model.candidate_id,
                    "canonical_symbol": candidate.symbol,
                    "symbol": candidate.symbol,
                    "action": candidate.action,
                    "account_id": self.DEFAULT_ACCOUNT_ID,
                    "broker_id": self.DEFAULT_BROKER_ID,
                    "lot": candidate.lot,
                    "confirm_demo_execution": request_model.confirm_demo_execution,
                    "live_execution_enabled": False,
                    "broker_execution_enabled": False,
                }
            )
            if not risk_decision.approved:
                return self.store.store_decision(
                    self._decision(
                        candidate,
                        request_model,
                        False,
                        "BLOCKED_RISK_ENGINE",
                        risk_decision.rejection_reasons,
                        risk_decision_id=risk_decision.decision_id,
                    )
                )

            queue_item = self._queue_item_from_candidate(candidate)
            demo_request = DemoExecutionRequest(
                queue_id=queue_item.queue_id,
                confirm_demo_execution=request_model.confirm_demo_execution,
                requested_by=request_model.requested_by or "unknown",
                reason=request_model.reason,
            )
            result = self.demo_execution_service.executor.execute_demo_order(queue_item, demo_request)
            result = self.demo_execution_service.result_store.store_result(result)
            mapped_status = self._map_demo_result_status(result.status)
            approved_for_execution = mapped_status in {"DEMO_EXECUTION_SENT", "DEMO_FILLED", "DEMO_REJECTED"}
            reasons = list(result.rejection_reasons)
            if mapped_status == "BLOCKED_DEMO_GUARD" and not reasons:
                reasons = ["Existing guarded MT5 demo executor blocked the request."]
            decision = self._decision(
                candidate,
                request_model,
                approved_for_execution,
                mapped_status,
                reasons,
                risk_decision_id=risk_decision.decision_id,
                demo_execution_result_id=result.execution_id,
                mt5_retcode=result.mt5_retcode,
                mt5_order=result.mt5_order,
                mt5_deal=result.mt5_deal,
            )
            if mapped_status == "DEMO_FILLED":
                copy_result = self.copier_bridge.distribute_execution(decision)
                decision.copier_execution_id = copy_result.copier_execution_id
                decision.copy_batch_id = copy_result.copy_batch_id
            return self.store.store_decision(decision)
        except Exception as exc:
            return self.store.store_decision(
                self._decision(candidate, request_model, False, "FAILED_SAFE", [f"Final demo execution failed safe: {exc}"])
            )

    def list_executions(self, limit: int = 100):
        return self.store.list_decisions(limit)

    def get_execution(self, final_execution_id: str):
        return self.store.get_decision(final_execution_id)

    def _queue_item_from_candidate(self, candidate: Any) -> ExecutionQueueItem:
        intent = ExecutionIntent(
            signal_id=candidate.decision_id,
            account_id=self.DEFAULT_ACCOUNT_ID,
            broker_id=self.DEFAULT_BROKER_ID,
            canonical_symbol=candidate.symbol,
            broker_symbol=candidate.symbol,
            action=candidate.action,
            allocated_lot=candidate.lot,
            order_type="MARKET",
            source="STRATEGY_EXECUTION_BRIDGE_FINAL_DEMO",
            simulation_only=True,
            live_execution_enabled=False,
        )
        return ExecutionQueueItem(
            queue_id=candidate.queue_preview_id,
            intent=intent,
            status="QUEUED",
            readiness="READY_FOR_DEMO_QUEUE",
            warnings=["Strategy execution bridge final demo handoff. Guarded executor only."],
            simulation_only=True,
            live_execution_enabled=False,
        )

    def _map_demo_result_status(self, status: str) -> str:
        if status == "DEMO_FILLED":
            return "DEMO_FILLED"
        if status == "DEMO_REJECTED":
            return "DEMO_REJECTED"
        if status == "MT5_UNAVAILABLE":
            return "MT5_UNAVAILABLE"
        if status == "FAILED_SAFE":
            return "FAILED_SAFE"
        return "BLOCKED_DEMO_GUARD"

    def _decision(
        self,
        candidate: Any | None,
        request: FinalDemoExecutionRequest,
        approved_for_execution: bool,
        status: str,
        reasons: list[str],
        risk_decision_id: str | None = None,
        demo_execution_result_id: str | None = None,
        mt5_retcode: int | str | None = None,
        mt5_order: int | str | None = None,
        mt5_deal: int | str | None = None,
    ) -> FinalDemoExecutionDecision:
        return FinalDemoExecutionDecision(
            candidate_id=request.candidate_id,
            approval_id=getattr(candidate, "approval_id", None),
            decision_id=getattr(candidate, "decision_id", None),
            queue_preview_id=getattr(candidate, "queue_preview_id", None),
            symbol=getattr(candidate, "symbol", None),
            action=getattr(candidate, "action", None),
            lot=float(getattr(candidate, "lot", 0.0) or 0.0),
            approved_for_execution=approved_for_execution,
            execution_status=status,
            rejection_reasons=reasons,
            risk_decision_id=risk_decision_id,
            demo_execution_result_id=demo_execution_result_id,
            mt5_retcode=mt5_retcode,
            mt5_order=mt5_order,
            mt5_deal=mt5_deal,
            simulation_only=True,
            demo_execution=True,
            live_execution_enabled=False,
            broker_execution_enabled=False,
        )
