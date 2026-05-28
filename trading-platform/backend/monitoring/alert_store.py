from collections import deque

from backend.monitoring.monitoring_models import AlertEvent


class AlertStore:
    """In-memory alert storage for dashboard monitoring."""

    def __init__(self, max_alerts: int = 1000) -> None:
        self.alerts: deque[AlertEvent] = deque(maxlen=max_alerts)

    def add_alert(self, alert: AlertEvent) -> AlertEvent:
        self.alerts.appendleft(alert)
        return alert

    def list_alerts(self, limit: int = 100) -> list[AlertEvent]:
        bounded_limit = max(1, min(int(limit), 1000))
        return list(self.alerts)[:bounded_limit]

    def acknowledge_alert(self, alert_id: str) -> AlertEvent | None:
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                return alert
        return None
