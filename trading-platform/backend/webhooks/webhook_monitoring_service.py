from typing import Any

from backend.webhooks.webhook_event_store import WebhookEventStore
from backend.webhooks.webhook_models import WebhookEventRecord


class WebhookMonitoringService:
    """Read-only monitoring facade for webhook ingestion events."""

    def __init__(self, store: WebhookEventStore | None = None) -> None:
        self.store = store or WebhookEventStore()

    def get_status(self) -> dict[str, Any]:
        recent = self.store.get_recent_events(500)
        return {
            "status": "operational",
            "mode": "TRADINGVIEW_WEBHOOK_INGESTION_ONLY",
            "events_stored": len(recent),
            "simulation_only": True,
            "live_execution_enabled": False,
        }

    def get_recent_events(self, limit: int = 50) -> list[WebhookEventRecord]:
        return self.store.get_recent_events(limit)

    def get_event(self, event_id: str) -> WebhookEventRecord | None:
        return self.store.get_event(event_id)
