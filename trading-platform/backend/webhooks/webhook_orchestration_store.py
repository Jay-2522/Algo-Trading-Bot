from collections import deque

from backend.webhooks.webhook_orchestration_models import WebhookOrchestrationDecision


class WebhookOrchestrationStore:
    """In-memory store for simulation-only webhook orchestration decisions."""

    def __init__(self, max_decisions: int = 500) -> None:
        self.decisions: deque[WebhookOrchestrationDecision] = deque(maxlen=max_decisions)

    def store_decision(self, decision: WebhookOrchestrationDecision) -> WebhookOrchestrationDecision:
        decision.simulation_only = True
        decision.live_execution_enabled = False
        self.decisions.appendleft(decision)
        return decision

    def get_recent_decisions(self, limit: int = 50) -> list[WebhookOrchestrationDecision]:
        bounded_limit = max(1, min(int(limit), 500))
        return list(self.decisions)[:bounded_limit]

    def get_decision(self, decision_id: str) -> WebhookOrchestrationDecision | None:
        for decision in self.decisions:
            if decision.decision_id == decision_id:
                return decision
        return None
