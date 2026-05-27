from typing import Any

from backend.webhooks.webhook_models import NormalizedTradingSignal
from backend.webhooks.webhook_orchestration_engine import WebhookOrchestrationEngine
from backend.webhooks.webhook_orchestration_models import WebhookOrchestrationDecision
from backend.webhooks.webhook_orchestration_store import WebhookOrchestrationStore


class WebhookOrchestrationService:
    """Service facade for webhook signal orchestration decisions."""

    def __init__(
        self,
        engine: WebhookOrchestrationEngine | None = None,
        store: WebhookOrchestrationStore | None = None,
    ) -> None:
        self.engine = engine or WebhookOrchestrationEngine()
        self.store = store or WebhookOrchestrationStore()

    def process_signal(self, signal: NormalizedTradingSignal) -> WebhookOrchestrationDecision:
        decision = self.engine.orchestrate_signal(signal)
        return self.store.store_decision(decision)

    def get_status(self) -> dict[str, Any]:
        return {
            "status": "operational",
            "mode": "WEBHOOK_SIGNAL_ORCHESTRATION_SIMULATION_ONLY",
            "decisions_stored": len(self.store.get_recent_decisions(500)),
            "simulation_only": True,
            "live_execution_enabled": False,
        }

    def get_recent_decisions(self, limit: int = 50) -> list[WebhookOrchestrationDecision]:
        return self.store.get_recent_decisions(limit)

    def get_decision(self, decision_id: str) -> WebhookOrchestrationDecision | None:
        return self.store.get_decision(decision_id)
