from datetime import datetime, timezone
from typing import Any

from backend.account_routing.account_registry import AccountRegistry
from backend.control_center.control_center_service import ControlCenterService
from backend.execution_risk.execution_risk_audit_store import ExecutionRiskAuditStore
from backend.execution_risk.execution_risk_models import ExecutionRiskDecision
from backend.execution_risk.execution_risk_policy import ExecutionRiskPolicyProvider
from backend.replay.symbol_normalizer import SymbolNormalizer


class ExecutionRiskEvaluator:
    """Evaluate demo execution and copy requests before execution workflow entry."""

    def __init__(
        self,
        policy_provider: ExecutionRiskPolicyProvider | None = None,
        audit_store: ExecutionRiskAuditStore | None = None,
        control_center_service: ControlCenterService | None = None,
        account_registry: AccountRegistry | None = None,
        normalizer: SymbolNormalizer | None = None,
    ) -> None:
        self.policy_provider = policy_provider or ExecutionRiskPolicyProvider()
        self.audit_store = audit_store or ExecutionRiskAuditStore()
        self.control_center_service = control_center_service or ControlCenterService()
        self.account_registry = account_registry or AccountRegistry()
        self.normalizer = normalizer or SymbolNormalizer()

    def evaluate_single_account_request(self, payload: dict[str, Any]) -> ExecutionRiskDecision:
        decision = self._evaluate(payload, target_accounts=1)
        return self.audit_store.store_decision(decision)

    def evaluate_multi_account_request(self, payload: dict[str, Any]) -> ExecutionRiskDecision:
        target_accounts = int(payload.get("target_account_count") or len(payload.get("target_accounts") or []) or 1)
        decision = self._evaluate(payload, target_accounts=target_accounts)
        return self.audit_store.store_decision(decision)

    def evaluate_copy_request(self, payload: dict[str, Any]) -> ExecutionRiskDecision:
        target_accounts = int(payload.get("target_account_count") or len(payload.get("target_accounts") or []) or 1)
        decision = self._evaluate(payload, target_accounts=target_accounts)
        return self.audit_store.store_decision(decision)

    def _evaluate(self, payload: dict[str, Any], target_accounts: int) -> ExecutionRiskDecision:
        policy = self.policy_provider.get_policy()
        symbol = self.normalizer.normalize(payload.get("canonical_symbol") or payload.get("symbol"))
        action = str(payload.get("action") or "").upper()
        lot = float(payload.get("lot") or payload.get("allocated_lot") or payload.get("requested_lot") or 0.0)
        request_id = str(payload.get("request_id") or payload.get("queue_id") or payload.get("signal_id") or "execution-risk-request")
        account_id = payload.get("account_id")
        broker_id = payload.get("broker_id")
        reasons: list[str] = []
        warnings = ["Execution risk enforcement is demo-only and performs no order placement."]

        if symbol in policy.blocked_symbols or symbol not in policy.allowed_symbols:
            reasons.append("Execution risk policy allows EURUSD only; requested symbol is blocked.")
        if action not in {"BUY", "SELL"}:
            reasons.append("Execution risk policy allows BUY/SELL only.")
        if lot <= 0:
            reasons.append("Per-account lot must be greater than zero.")
        if lot > policy.max_lot_per_account:
            reasons.append("Per-account lot must be <= 0.01.")
        if target_accounts > policy.max_target_accounts:
            reasons.append("Target account count must be <= 3.")
        if policy.require_confirmation and not bool(payload.get("confirm_demo_execution")):
            reasons.append("confirm_demo_execution must be true.")
        if bool(payload.get("live_execution_enabled")) or policy.live_execution_enabled:
            reasons.append("Live execution is disabled by execution risk policy.")
        if bool(payload.get("broker_execution_enabled")) or policy.broker_execution_enabled:
            reasons.append("Broker execution is disabled by execution risk policy.")
        if policy.require_demo_account and account_id and not self._account_eligible(str(account_id), symbol):
            reasons.append("Target account is not eligible for demo execution risk policy.")
        reasons.extend(self._safety_rejections())
        reasons.extend(self._daily_attempt_rejections(policy.max_daily_demo_attempts))

        approved = not reasons
        return ExecutionRiskDecision(
            request_id=request_id,
            canonical_symbol=symbol,
            action=action,
            account_id=str(account_id) if account_id is not None else None,
            broker_id=str(broker_id) if broker_id is not None else None,
            lot=lot,
            approved=approved,
            risk_level="LOW" if approved else "BLOCKED",
            rejection_reasons=reasons,
            warnings=warnings,
            simulation_only=True,
            demo_execution=True,
            live_execution_enabled=False,
            broker_execution_enabled=False,
        )

    def _account_eligible(self, account_id: str, symbol: str) -> bool:
        account = self.account_registry.get_account(account_id)
        return bool(account and account.enabled and account.demo_ready and symbol in account.supported_symbols)

    def _safety_rejections(self) -> list[str]:
        try:
            state = self.control_center_service.get_safety_state()
            reasons: list[str] = []
            if getattr(state, "queue_paused", False):
                reasons.append("Simulation queue is paused.")
            if getattr(state, "emergency_stop_active", False):
                reasons.append("Emergency stop placeholder is active.")
            return reasons
        except Exception:
            return ["Safety control state is unavailable."]

    def _daily_attempt_rejections(self, max_daily_demo_attempts: int) -> list[str]:
        today = datetime.now(timezone.utc).date()
        today_count = sum(
            1
            for decision in self.audit_store.list_decisions(1000)
            if decision.timestamp.date() == today
        )
        if today_count >= max_daily_demo_attempts:
            return ["Maximum daily demo execution attempts reached."]
        return []
