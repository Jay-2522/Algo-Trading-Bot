from collections import deque

from backend.webhooks.webhook_models import WebhookEventRecord


class WebhookEventStore:
    """Small in-memory event store for safe webhook monitoring."""

    def __init__(self, max_events: int = 500) -> None:
        self.events: deque[WebhookEventRecord] = deque(maxlen=max_events)

    def store_event(self, event: WebhookEventRecord) -> WebhookEventRecord:
        event.simulation_only = True
        event.live_execution_enabled = False
        self.events.appendleft(event)
        return event

    def get_recent_events(self, limit: int = 50) -> list[WebhookEventRecord]:
        bounded_limit = max(1, min(int(limit), 500))
        return list(self.events)[:bounded_limit]

    def get_event(self, event_id: str) -> WebhookEventRecord | None:
        for event in self.events:
            if event.event_id == event_id:
                return event
        return None
