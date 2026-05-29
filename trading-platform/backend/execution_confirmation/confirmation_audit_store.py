from collections import deque
from typing import Any

from backend.execution_confirmation.confirmation_models import ConfirmationAuditEvent


class ConfirmationAuditStore:
    """In-memory audit trail for read-only execution confirmation reconciliation."""

    def __init__(self, max_events: int = 1000) -> None:
        self.events: deque[ConfirmationAuditEvent] = deque(maxlen=max_events)

    def store_event(
        self,
        event_type: str,
        message: str,
        execution_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ConfirmationAuditEvent:
        event = ConfirmationAuditEvent(
            event_type=event_type,
            execution_id=execution_id,
            message=message,
            metadata=metadata or {},
            simulation_only=True,
            demo_execution=True,
            live_execution_enabled=False,
            broker_execution_enabled=False,
        )
        self.events.appendleft(event)
        return event

    def list_events(self, limit: int = 100) -> list[ConfirmationAuditEvent]:
        bounded_limit = max(1, min(int(limit), 1000))
        return list(self.events)[:bounded_limit]
