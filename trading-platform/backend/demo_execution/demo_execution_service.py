from typing import Any

from backend.demo_execution.demo_execution_models import DemoExecutionRequest, DemoExecutionResult, MT5DemoAccountStatus
from backend.demo_execution.demo_execution_result_store import DemoExecutionResultStore
from backend.demo_execution.mt5_demo_account_verifier import MT5DemoAccountVerifier
from backend.demo_execution.mt5_demo_executor import MT5DemoExecutor
from backend.execution_queue.execution_queue_service import ExecutionQueueService


class DemoExecutionService:
    """Facade for guarded MT5 demo execution from queue items."""

    def __init__(
        self,
        execution_queue_service: ExecutionQueueService | None = None,
        account_verifier: MT5DemoAccountVerifier | None = None,
        executor: MT5DemoExecutor | None = None,
        result_store: DemoExecutionResultStore | None = None,
    ) -> None:
        self.execution_queue_service = execution_queue_service or ExecutionQueueService()
        self.account_verifier = account_verifier or MT5DemoAccountVerifier()
        self.executor = executor or MT5DemoExecutor()
        self.result_store = result_store or DemoExecutionResultStore()

    def get_status(self) -> dict[str, Any]:
        account_status = self.verify_account()
        return {
            "status": "DEMO_EXECUTION_READY" if account_status.demo_execution_allowed else "DEMO_EXECUTION_BLOCKED",
            "mode": "MT5_DEMO_EXECUTION_ONLY",
            "demo_execution_enabled": True,
            "allowed_symbol": "EURUSD",
            "max_lot": 0.01,
            "market_orders_only": True,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "account": account_status.model_dump(mode="json"),
        }

    def verify_account(self) -> MT5DemoAccountStatus:
        return self.account_verifier.verify_demo_account()

    def execute_queue_item_demo(self, queue_id: str, request: DemoExecutionRequest | dict[str, Any]) -> DemoExecutionResult:
        parsed_request = request if isinstance(request, DemoExecutionRequest) else DemoExecutionRequest(queue_id=queue_id, **request)
        item = self.execution_queue_service.get_item(queue_id)
        result = self.executor.execute_demo_order(item, parsed_request)
        return self.result_store.store_result(result)

    def list_results(self, limit: int = 100) -> list[DemoExecutionResult]:
        return self.result_store.list_results(limit)

    def get_result(self, execution_id: str) -> DemoExecutionResult | None:
        return self.result_store.get_result(execution_id)
