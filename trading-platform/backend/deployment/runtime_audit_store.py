from datetime import datetime, timezone
from uuid import uuid4


class RuntimeAuditStore:
    """In-memory audit store for read-only runtime checks and manual-control visibility."""

    _events: list[dict] = []

    def store_event(self, event: dict) -> dict:
        stored = {
            "event_id": event.get("event_id") or f"runtime_audit_{uuid4().hex[:12]}",
            "event_type": event.get("event_type", "RUNTIME_STATUS_CHECK"),
            "message": event.get("message", "Runtime audit event recorded."),
            "metadata": event.get("metadata", {}),
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "timestamp": event.get("timestamp") or datetime.now(timezone.utc),
        }
        self._events.insert(0, stored)
        del self._events[1000:]
        return stored

    def list_events(self, limit: int = 100) -> list[dict]:
        return self._events[: max(1, min(int(limit), 1000))]
