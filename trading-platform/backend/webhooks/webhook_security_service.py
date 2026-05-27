from typing import Any

from backend.webhooks.webhook_audit_logger import WebhookAuditLogger
from backend.webhooks.webhook_security_models import WebhookSecurityEvent
from backend.webhooks.webhook_security_monitor import WebhookSecurityMonitor


class WebhookSecurityService:
    """Security facade for webhook replay protection, rate limiting, and auditing."""

    def __init__(
        self,
        monitor: WebhookSecurityMonitor | None = None,
        audit_logger: WebhookAuditLogger | None = None,
    ) -> None:
        self.monitor = monitor or WebhookSecurityMonitor()
        self.audit_logger = audit_logger or WebhookAuditLogger()

    def validate_webhook_request(self, payload: dict[str, Any] | None, source_ip: str | None) -> WebhookSecurityEvent:
        event = self.monitor.classify_request(payload, source_ip)
        return self.audit_logger.log_security_event(event)

    def get_status(self) -> dict[str, Any]:
        return {
            "status": "operational",
            "mode": "WEBHOOK_SECURITY_HARDENING_ONLY",
            "events_logged": len(self.audit_logger.get_recent_events(1000)),
            "simulation_only": True,
            "live_execution_enabled": False,
        }

    def get_security_events(self, limit: int = 100) -> list[WebhookSecurityEvent]:
        return self.audit_logger.get_recent_events(limit)
