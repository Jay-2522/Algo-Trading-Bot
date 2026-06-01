from backend.strategy_execution_bridge.execution_operations_models import ExecutionPipelineEvent


class ExecutionOperationsAudit:
    """In-memory read-only operations audit for pipeline visibility events."""

    _events: list[ExecutionPipelineEvent] = []

    def store_event(self, event: ExecutionPipelineEvent | dict) -> ExecutionPipelineEvent:
        parsed = event if isinstance(event, ExecutionPipelineEvent) else ExecutionPipelineEvent(**event)
        self._events.insert(0, parsed)
        del self._events[1000:]
        return parsed

    def list_events(self, limit: int = 100) -> list[ExecutionPipelineEvent]:
        return self._events[: max(1, min(int(limit), 1000))]
