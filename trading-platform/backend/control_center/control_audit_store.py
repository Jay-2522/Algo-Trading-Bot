from collections import deque
from typing import Any

from backend.control_center.control_models import ControlActionType, ControlAuditEvent


class ControlAuditStore:
    """In-memory audit trail for simulation-only operator controls."""

    def __init__(self, max_events: int = 1000) -> None:
        self.events: deque[ControlAuditEvent] = deque(maxlen=max_events)

    def log_event(self, action_type: ControlActionType, reason: str, result: dict[str, Any]) -> ControlAuditEvent:
        event = ControlAuditEvent(action_type=action_type, reason=reason or "No reason provided.", result=result)
        self.events.appendleft(event)
        return event

    def get_recent_events(self, limit: int = 100) -> list[ControlAuditEvent]:
        bounded_limit = max(1, min(int(limit), 1000))
        return list(self.events)[:bounded_limit]
