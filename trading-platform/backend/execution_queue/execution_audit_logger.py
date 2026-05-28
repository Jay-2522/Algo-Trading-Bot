from collections import deque
from typing import Any

from backend.execution_queue.execution_lifecycle_models import ExecutionAuditEvent


class ExecutionAuditLogger:
    """JSON-safe audit trail for simulated execution events."""

    def __init__(self, max_events: int = 1000) -> None:
        self.events: deque[ExecutionAuditEvent] = deque(maxlen=max_events)

    def log_event(
        self,
        queue_id: str,
        event_type: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionAuditEvent:
        event = ExecutionAuditEvent(
            queue_id=queue_id,
            event_type=event_type,
            message=message,
            metadata=metadata or {},
        )
        self.events.appendleft(event)
        return event

    def get_events(self, limit: int = 100) -> list[ExecutionAuditEvent]:
        bounded_limit = max(1, min(int(limit), 1000))
        return list(self.events)[:bounded_limit]

    def get_events_for_queue(self, queue_id: str) -> list[ExecutionAuditEvent]:
        return [event for event in self.events if event.queue_id == queue_id]
