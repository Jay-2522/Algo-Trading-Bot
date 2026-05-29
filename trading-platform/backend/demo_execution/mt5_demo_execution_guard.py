from backend.control_center.control_center_service import ControlCenterService
from backend.demo_execution.demo_execution_models import DemoExecutionRequest, MT5DemoAccountStatus
from backend.demo_execution.mt5_demo_account_verifier import MT5DemoAccountVerifier
from backend.execution_queue.execution_queue_models import ExecutionQueueItem
from backend.execution_risk.execution_risk_evaluator import ExecutionRiskEvaluator


class MT5DemoExecutionGuard:
    """Hard gatekeeper for demo execution requests."""

    def __init__(
        self,
        account_verifier: MT5DemoAccountVerifier | None = None,
        control_center_service: ControlCenterService | None = None,
        risk_evaluator: ExecutionRiskEvaluator | None = None,
        demo_execution_enabled: bool = True,
    ) -> None:
        self.account_verifier = account_verifier or MT5DemoAccountVerifier()
        self.control_center_service = control_center_service or ControlCenterService()
        self.risk_evaluator = risk_evaluator or ExecutionRiskEvaluator(control_center_service=self.control_center_service)
        self.demo_execution_enabled = demo_execution_enabled

    def validate_demo_execution(
        self,
        queue_item: ExecutionQueueItem | None,
        request: DemoExecutionRequest,
    ) -> tuple[bool, list[str], MT5DemoAccountStatus]:
        reasons: list[str] = []
        account_status = self.account_verifier.verify_demo_account()
        if not account_status.demo_execution_allowed:
            reasons.extend(account_status.rejection_reasons or ["MT5 demo account is not verified."])
        if not self.demo_execution_enabled:
            reasons.append("Demo execution is disabled.")
        if not request.confirm_demo_execution:
            reasons.append("confirm_demo_execution must be true.")
        if queue_item is None:
            reasons.append("Execution queue item was not found.")
            return False, reasons, account_status

        state = self.control_center_service.get_safety_state()
        if state.queue_paused:
            reasons.append("Simulation queue is paused.")
        if state.emergency_stop_active:
            reasons.append("Emergency stop placeholder is active.")
        if queue_item.readiness != "READY_FOR_DEMO_QUEUE" or queue_item.status != "QUEUED":
            reasons.append("Queue item is not ready for demo execution.")
        if queue_item.live_execution_enabled:
            reasons.append("Queue item indicates live execution; blocked.")

        intent = queue_item.intent
        if (intent.canonical_symbol or "").upper() != "EURUSD":
            reasons.append("Phase 5 Day 1 allows EURUSD demo execution only.")
        if (intent.action or "").upper() not in {"BUY", "SELL"}:
            reasons.append("Phase 5 Day 1 allows BUY/SELL only.")
        if intent.order_type != "MARKET":
            reasons.append("Phase 5 Day 1 allows MARKET orders only.")
        if float(intent.allocated_lot or 0.0) > 0.01:
            reasons.append("Demo execution lot must be <= 0.01.")
        if float(intent.allocated_lot or 0.0) <= 0:
            reasons.append("Demo execution lot must be greater than zero.")
        if intent.live_execution_enabled:
            reasons.append("Intent indicates live execution; blocked.")
        risk_decision = self.risk_evaluator.evaluate_single_account_request(
            {
                "request_id": request.queue_id,
                "queue_id": request.queue_id,
                "canonical_symbol": intent.canonical_symbol,
                "action": intent.action,
                "account_id": intent.account_id,
                "broker_id": intent.broker_id,
                "lot": intent.allocated_lot,
                "confirm_demo_execution": request.confirm_demo_execution,
                "live_execution_enabled": intent.live_execution_enabled or queue_item.live_execution_enabled,
                "broker_execution_enabled": False,
            }
        )
        if not risk_decision.approved:
            reasons.extend(f"Execution risk blocked: {reason}" for reason in risk_decision.rejection_reasons)

        return not reasons, reasons, account_status
