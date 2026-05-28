from typing import Any

from backend.monitoring.alert_store import AlertStore
from backend.monitoring.monitoring_models import AlertEvent


class AlertEngine:
    """Create and classify monitoring alert events."""

    def __init__(self, alert_store: AlertStore | None = None) -> None:
        self.alert_store = alert_store or AlertStore()

    def create_alert(self, severity: str, source: str, title: str, message: str) -> AlertEvent:
        alert = AlertEvent(
            severity=severity,
            source=source,
            title=title,
            message=message,
        )
        return self.alert_store.add_alert(alert)

    def classify_event(self, event: dict[str, Any]) -> AlertEvent | None:
        event_type = str(event.get("event_type") or event.get("status") or "").upper()
        if "FAILED" in event_type:
            return self.create_alert("ERROR", str(event.get("source", "system")), "Module failure", str(event))
        if "REPLAY_ATTACK" in event_type or "RATE_LIMIT" in event_type:
            return self.create_alert("WARNING", "webhooks", "Suspicious webhook activity", str(event))
        if "SIMULATED_REJECTED" in event_type or "FAILED_SAFE" in event_type:
            return self.create_alert("ERROR", "execution_queue", "Execution simulation issue", str(event))
        if "BLOCKED" in event_type:
            return self.create_alert("WARNING", str(event.get("source", "system")), "Blocked activity", str(event))
        return None
