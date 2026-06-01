class CopierExecutionStore:
    """In-memory audit store for strategy execution to trade copier distributions."""

    _results: dict[str, object] = {}

    def store_result(self, result):
        self._results[result.copier_execution_id] = result
        return result

    def list_results(self, limit: int = 100) -> list:
        return sorted(self._results.values(), key=lambda result: result.timestamp, reverse=True)[:limit]

    def get_result(self, copier_execution_id: str):
        return self._results.get(copier_execution_id)
