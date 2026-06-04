from backend.nifty50.indian_broker_registry import IndianBrokerRegistry
from backend.nifty50.nifty_execution_models import NIFTYExecutionIntent
from backend.nifty50.nifty_risk_models import NIFTYTradeCandidate


class NIFTYExecutionValidator:
    def __init__(self, broker_registry: IndianBrokerRegistry | None = None) -> None:
        self.broker_registry = broker_registry or IndianBrokerRegistry()

    def validate_candidate(self, candidate: NIFTYTradeCandidate) -> list[str]:
        reasons: list[str] = []
        if candidate.action == "WAIT":
            reasons.append("WAIT candidate cannot be converted to execution intent.")
        if not candidate.qualified:
            reasons.append("Candidate is not qualified.")
        if not candidate.execution_allowed:
            reasons.append("Execution is disabled for NIFTY50 candidates.")
        return reasons

    def validate_intent(self, intent: NIFTYExecutionIntent) -> list[str]:
        reasons: list[str] = []
        if intent.action == "WAIT":
            reasons.append("WAIT action cannot be previewed as an executable order.")
        if intent.symbol != "NIFTY50":
            reasons.append("Only NIFTY50 intents are supported.")
        if intent.quantity <= 0:
            reasons.append("Quantity must be greater than zero.")
        if not intent.broker_id:
            reasons.append("Broker not selected.")
        elif self.broker_registry.get_broker(intent.broker_id) is None:
            reasons.append("Broker not recognized.")
        if not intent.execution_allowed:
            reasons.append("Execution disabled; preview only.")
        if intent.live_execution_enabled:
            reasons.append("Unexpected live execution flag enabled.")
        if not intent.broker_execution_enabled:
            reasons.append("Broker execution disabled.")
        return reasons
