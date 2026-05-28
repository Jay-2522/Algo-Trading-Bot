from backend.webhooks.tradingview_webhook_service import TradingViewWebhookService
from backend.webhooks.webhook_monitoring_service import WebhookMonitoringService
from backend.webhooks.webhook_orchestration_service import WebhookOrchestrationService


class WebhookMonitor:
    """Summarize webhook ingestion, security, and orchestration activity."""

    def __init__(
        self,
        tradingview_service: TradingViewWebhookService | None = None,
        orchestration_service: WebhookOrchestrationService | None = None,
    ) -> None:
        self.tradingview_service = tradingview_service or TradingViewWebhookService()
        self.monitoring_service = WebhookMonitoringService(self.tradingview_service.store)
        self.orchestration_service = orchestration_service or WebhookOrchestrationService()

    def get_webhook_metrics(self) -> dict:
        events = self.monitoring_service.get_recent_events(500)
        security_events = self.tradingview_service.security_service.get_security_events(500)
        decisions = self.orchestration_service.get_recent_decisions(500)
        return {
            "webhook_requests": len(events),
            "rejected_requests": len([event for event in events if event.processing_status == "REJECTED"]),
            "replay_attacks": len([event for event in security_events if event.event_type == "REPLAY_ATTACK"]),
            "rate_limits": len([event for event in security_events if event.event_type == "RATE_LIMIT"]),
            "orchestration_requests": len(decisions),
            "simulation_only": True,
            "live_execution_enabled": False,
        }
