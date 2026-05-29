from typing import Any

from backend.execution_queue.execution_lifecycle_models import ExecutionAuditEvent
from backend.multi_account_execution.account_execution_planner import AccountExecutionPlanner
from backend.multi_account_execution.multi_account_demo_executor import MultiAccountDemoExecutor
from backend.multi_account_execution.multi_account_models import AccountDemoExecutionPlan, MultiAccountDemoExecutionResult
from backend.multi_account_execution.multi_account_result_store import MultiAccountResultStore


class MultiAccountExecutionService:
    """Service facade for Phase 5 multi-account MT5 demo routing."""

    def __init__(
        self,
        planner: AccountExecutionPlanner | None = None,
        executor: MultiAccountDemoExecutor | None = None,
        result_store: MultiAccountResultStore | None = None,
    ) -> None:
        self.result_store = result_store or MultiAccountResultStore()
        self.planner = planner or AccountExecutionPlanner()
        self.executor = executor or MultiAccountDemoExecutor(planner=self.planner, result_store=self.result_store)

    def get_status(self) -> dict[str, Any]:
        return {
            "status": "OPERATIONAL",
            "mode": "MULTI_ACCOUNT_MT5_DEMO_ROUTING_ONLY",
            "target_accounts": ["STARTRADER_DEMO_1", "FXPRO_DEMO_1", "VANTAGE_DEMO_1"],
            "allowed_symbol": "EURUSD",
            "max_lot_per_account": 0.01,
            "max_target_accounts": 3,
            "demo_execution_enabled": True,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def preview_plans(self, signal_payload: dict[str, Any]) -> list[AccountDemoExecutionPlan]:
        return self.planner.build_plans(signal_payload)

    def execute_demo_batch(self, signal_payload: dict[str, Any]) -> MultiAccountDemoExecutionResult:
        return self.executor.execute_batch(signal_payload)

    def list_results(self, limit: int = 100) -> list[MultiAccountDemoExecutionResult]:
        return self.result_store.list_results(limit)

    def get_result(self, batch_id: str) -> MultiAccountDemoExecutionResult | None:
        return self.result_store.get_result(batch_id)

    def get_audit_events(self, limit: int = 100) -> list[ExecutionAuditEvent]:
        return self.executor.audit_logger.get_events(limit)
