from typing import Any

from backend.strategy_execution_bridge.approval_guard import ApprovalGuard
from backend.strategy_execution_bridge.bridge_decision_store import BridgeDecisionStore
from backend.strategy_execution_bridge.demo_approval_models import (
    DemoExecutionApprovalDecision,
    DemoExecutionApprovalRequest,
    DemoExecutionCandidate,
)
from backend.strategy_execution_bridge.demo_execution_approval_store import DemoExecutionApprovalStore


class DemoExecutionApprovalService:
    """Approve queue previews into demo execution candidates without executing orders."""

    def __init__(
        self,
        bridge_store: BridgeDecisionStore | None = None,
        approval_store: DemoExecutionApprovalStore | None = None,
        guard: ApprovalGuard | None = None,
    ) -> None:
        self.bridge_store = bridge_store or BridgeDecisionStore()
        self.approval_store = approval_store or DemoExecutionApprovalStore()
        self.guard = guard or ApprovalGuard()

    def get_status(self) -> dict[str, Any]:
        return {
            "status": "OPERATIONAL",
            "mode": "DEMO_EXECUTION_APPROVAL_FLOW",
            "approval_only": True,
            "requires_explicit_demo_approval": True,
            "requires_final_execution_confirmation": True,
            "stale_preview_minutes": self.guard.STALE_MINUTES,
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def approve_decision(self, request: DemoExecutionApprovalRequest | dict[str, Any]) -> DemoExecutionApprovalDecision:
        request_model = request if isinstance(request, DemoExecutionApprovalRequest) else DemoExecutionApprovalRequest(**request)
        decision = self.bridge_store.get_decision(request_model.decision_id)
        already_approved = self.approval_store.has_existing_approval(request_model.decision_id)
        try:
            approved, status, reasons = self.guard.validate(
                decision,
                request_model,
                already_approved=already_approved,
            )
            if not approved:
                return self.approval_store.store_approval(
                    self._approval_from_decision(
                        decision=decision,
                        request=request_model,
                        approved=False,
                        status=status,
                        reasons=reasons,
                    )
                )

            approval = self._approval_from_decision(
                decision=decision,
                request=request_model,
                approved=True,
                status="APPROVED_FOR_DEMO_EXECUTION",
                reasons=[],
            )
            candidate = self._candidate_from_decision(approval, decision)
            self.approval_store.store_candidate(candidate)
            approval.demo_execution_candidate_id = candidate.candidate_id
            return self.approval_store.store_approval(approval)
        except Exception as exc:
            return self.approval_store.store_approval(
                self._approval_from_decision(
                    decision=decision,
                    request=request_model,
                    approved=False,
                    status="FAILED_SAFE",
                    reasons=[f"Approval failed safe: {exc}"],
                )
            )

    def list_approvals(self, limit: int = 100):
        return self.approval_store.list_approvals(limit)

    def get_approval(self, approval_id: str):
        return self.approval_store.get_approval(approval_id)

    def list_candidates(self, limit: int = 100):
        return self.approval_store.list_candidates(limit)

    def get_candidate(self, candidate_id: str):
        return self.approval_store.get_candidate(candidate_id)

    def _approval_from_decision(
        self,
        decision: Any | None,
        request: DemoExecutionApprovalRequest,
        approved: bool,
        status: str,
        reasons: list[str],
    ) -> DemoExecutionApprovalDecision:
        return DemoExecutionApprovalDecision(
            decision_id=request.decision_id,
            signal_id=self._get(decision, "signal_id", None),
            symbol=self._get(decision, "symbol", None),
            action=self._get(decision, "action", None),
            queue_preview_id=self._get(decision, "queue_preview_id", None),
            approved=approved,
            approval_status=status,
            rejection_reasons=reasons,
            simulation_only=True,
            demo_execution=True,
            live_execution_enabled=False,
            broker_execution_enabled=False,
        )

    def _candidate_from_decision(self, approval: DemoExecutionApprovalDecision, decision: Any) -> DemoExecutionCandidate:
        intent = self._get(decision, "mapped_intent", None)
        return DemoExecutionCandidate(
            approval_id=approval.approval_id,
            decision_id=approval.decision_id,
            queue_preview_id=str(approval.queue_preview_id),
            symbol=str(approval.symbol),
            action=str(approval.action),
            lot=float(self._get(intent, "total_lot", 0.01) or 0.01),
            allocation_mode=str(self._get(intent, "allocation_mode", "EQUAL")),
            strategy_name=str(self._get(intent, "strategy_name", "UNKNOWN_STRATEGY")),
            ready_for_demo_execution=True,
            requires_final_execution_confirmation=True,
            simulation_only=True,
            demo_execution=True,
            live_execution_enabled=False,
        )

    def _get(self, obj: Any | None, key: str, default: Any) -> Any:
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)
