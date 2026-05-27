from collections import deque

from backend.webhooks.webhook_security_models import WebhookSecurityEvent


class WebhookAuditLogger:
    """In-memory JSON-safe security audit trail."""

    def __init__(self, max_events: int = 1000) -> None:
        self.events: deque[WebhookSecurityEvent] = deque(maxlen=max_events)

    def log_security_event(self, event: WebhookSecurityEvent) -> WebhookSecurityEvent:
        self.events.appendleft(event)
        return event

    def get_recent_events(self, limit: int = 100) -> list[WebhookSecurityEvent]:
        bounded_limit = max(1, min(int(limit), 1000))
        return list(self.events)[:bounded_limit]
