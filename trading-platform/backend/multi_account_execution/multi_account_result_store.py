from collections import deque

from backend.multi_account_execution.multi_account_models import MultiAccountDemoExecutionResult


class MultiAccountResultStore:
    """In-memory audit store for multi-account demo execution batches."""

    def __init__(self, max_results: int = 1000) -> None:
        self.results: deque[MultiAccountDemoExecutionResult] = deque(maxlen=max_results)

    def store_result(self, result: MultiAccountDemoExecutionResult) -> MultiAccountDemoExecutionResult:
        result.simulation_only = True
        result.demo_execution = True
        result.live_execution_enabled = False
        result.broker_execution_enabled = False
        self.results.appendleft(result)
        return result

    def list_results(self, limit: int = 100) -> list[MultiAccountDemoExecutionResult]:
        bounded_limit = max(1, min(int(limit), 1000))
        return list(self.results)[:bounded_limit]

    def get_result(self, batch_id: str) -> MultiAccountDemoExecutionResult | None:
        for result in self.results:
            if result.batch_id == batch_id:
                return result
        return None

    def has_account_execution(self, signal_id: str, account_id: str) -> bool:
        for result in self.results:
            if result.signal_id != signal_id:
                continue
            if any(account.account_id == account_id for account in result.account_results):
                return True
        return False
