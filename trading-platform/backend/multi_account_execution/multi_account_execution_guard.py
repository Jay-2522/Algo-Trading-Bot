from typing import Any

from backend.control_center.control_center_service import ControlCenterService
from backend.demo_execution.mt5_demo_account_verifier import MT5DemoAccountVerifier
from backend.execution_risk.execution_risk_evaluator import ExecutionRiskEvaluator
from backend.multi_account_execution.multi_account_models import AccountDemoExecutionPlan
from backend.multi_account_execution.multi_account_result_store import MultiAccountResultStore


class MultiAccountExecutionGuard:
    """Validate per-account demo execution plans before any guarded demo attempt."""

    def __init__(
        self,
        account_verifier: MT5DemoAccountVerifier | None = None,
        control_center_service: ControlCenterService | None = None,
        risk_evaluator: ExecutionRiskEvaluator | None = None,
        result_store: MultiAccountResultStore | None = None,
    ) -> None:
        self.account_verifier = account_verifier or MT5DemoAccountVerifier()
        self.control_center_service = control_center_service or ControlCenterService()
        self.risk_evaluator = risk_evaluator or ExecutionRiskEvaluator(control_center_service=self.control_center_service)
        self.result_store = result_store or MultiAccountResultStore()

    def validate_plan(self, plan: AccountDemoExecutionPlan) -> tuple[bool, list[str]]:
        reasons = list(plan.rejection_reasons)
        account_status = self.account_verifier.verify_demo_account()
        if not account_status.demo_execution_allowed:
            reasons.extend(account_status.rejection_reasons or ["MT5 demo account is not verified."])
        if self.result_store.has_account_execution(plan.signal_id, plan.account_id):
            reasons.append("Duplicate demo execution attempt for this signal/account is blocked.")
        try:
            state = self.control_center_service.get_safety_state()
            if state.queue_paused:
                reasons.append("Simulation queue is paused.")
            if state.emergency_stop_active:
                reasons.append("Emergency stop placeholder is active.")
        except Exception:
            reasons.append("Safety control state is unavailable.")
        if plan.canonical_symbol != "EURUSD":
            reasons.append("Phase 5 Day 3 allows EURUSD demo execution only.")
        if plan.action not in {"BUY", "SELL"}:
            reasons.append("Phase 5 Day 3 allows BUY/SELL only.")
        if plan.order_type != "MARKET":
            reasons.append("Phase 5 Day 3 allows MARKET orders only.")
        if plan.lot <= 0:
            reasons.append("Per-account demo lot must be greater than zero.")
        if plan.lot > 0.01:
            reasons.append("Per-account demo lot must be <= 0.01.")
        if plan.live_execution_enabled:
            reasons.append("Plan indicates live execution; blocked.")
        risk_decision = self.risk_evaluator.evaluate_single_account_request(
            {
                "request_id": plan.plan_id,
                "canonical_symbol": plan.canonical_symbol,
                "action": plan.action,
                "account_id": plan.account_id,
                "broker_id": plan.broker_id,
                "lot": plan.lot,
                "confirm_demo_execution": True,
                "live_execution_enabled": plan.live_execution_enabled,
                "broker_execution_enabled": False,
            }
        )
        if not risk_decision.approved:
            reasons.extend(f"Execution risk blocked: {reason}" for reason in risk_decision.rejection_reasons)
        return not reasons, reasons

    def validate_batch(self, plans: list[AccountDemoExecutionPlan]) -> tuple[bool, list[str]]:
        reasons: list[str] = []
        if len(plans) > 3:
            reasons.append("Phase 5 Day 3 allows a maximum of 3 target demo accounts.")
        for plan in plans:
            _allowed, plan_reasons = self.validate_plan(plan)
            reasons.extend(f"{plan.account_id}: {reason}" for reason in plan_reasons)
        return not reasons, reasons
