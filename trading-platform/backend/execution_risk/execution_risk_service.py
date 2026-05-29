from typing import Any

from backend.execution_risk.execution_risk_audit_store import ExecutionRiskAuditStore
from backend.execution_risk.execution_risk_evaluator import ExecutionRiskEvaluator
from backend.execution_risk.execution_risk_models import ExecutionRiskDecision, ExecutionRiskPolicy
from backend.execution_risk.execution_risk_policy import ExecutionRiskPolicyProvider


class ExecutionRiskService:
    """Service facade for Phase 5 execution-time risk enforcement."""

    def __init__(
        self,
        policy_provider: ExecutionRiskPolicyProvider | None = None,
        evaluator: ExecutionRiskEvaluator | None = None,
        audit_store: ExecutionRiskAuditStore | None = None,
    ) -> None:
        self.audit_store = audit_store or ExecutionRiskAuditStore()
        self.policy_provider = policy_provider or ExecutionRiskPolicyProvider()
        self.evaluator = evaluator or ExecutionRiskEvaluator(
            policy_provider=self.policy_provider,
            audit_store=self.audit_store,
        )

    def get_status(self) -> dict[str, Any]:
        return {
            "status": "OPERATIONAL",
            "mode": "DEMO_EXECUTION_RISK_ENFORCEMENT",
            "decisions_recorded": len(self.audit_store.list_decisions(1000)),
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def get_policy(self) -> ExecutionRiskPolicy:
        return self.policy_provider.get_policy()

    def evaluate(self, payload: dict[str, Any]) -> ExecutionRiskDecision:
        request_type = str(payload.get("request_type") or "single").lower()
        if request_type in {"multi", "multi_account"}:
            return self.evaluator.evaluate_multi_account_request(payload)
        if request_type in {"copy", "trade_copy", "trade_copier"}:
            return self.evaluator.evaluate_copy_request(payload)
        return self.evaluator.evaluate_single_account_request(payload)

    def list_decisions(self, limit: int = 100) -> list[ExecutionRiskDecision]:
        return self.audit_store.list_decisions(limit)

    def list_events(self, limit: int = 100) -> list[Any]:
        return self.audit_store.list_events(limit)
