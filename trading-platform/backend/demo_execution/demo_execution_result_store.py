from collections import deque

from backend.demo_execution.demo_execution_models import DemoExecutionResult


class DemoExecutionResultStore:
    """In-memory audit store for guarded MT5 demo execution attempts."""

    def __init__(self, max_results: int = 1000) -> None:
        self.results: deque[DemoExecutionResult] = deque(maxlen=max_results)

    def store_result(self, result: DemoExecutionResult) -> DemoExecutionResult:
        result.simulation_only = True
        result.live_execution_enabled = False
        result.broker_execution_enabled = False
        result.demo_execution = True
        self.results.appendleft(result)
        return result

    def list_results(self, limit: int = 100) -> list[DemoExecutionResult]:
        bounded_limit = max(1, min(int(limit), 1000))
        return list(self.results)[:bounded_limit]

    def get_result(self, execution_id: str) -> DemoExecutionResult | None:
        for result in self.results:
            if result.execution_id == execution_id:
                return result
        return None

    def get_result_for_queue(self, queue_id: str) -> DemoExecutionResult | None:
        for result in self.results:
            if result.queue_id == queue_id:
                return result
        return None

    def has_queue_execution(self, queue_id: str) -> bool:
        return self.get_result_for_queue(queue_id) is not None
