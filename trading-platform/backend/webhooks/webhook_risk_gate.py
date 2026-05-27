from backend.replay.client_symbol_registry import ClientSymbolRegistry
from backend.webhooks.webhook_models import NormalizedTradingSignal
from backend.webhooks.webhook_orchestration_models import WebhookRiskGateResult


class WebhookRiskGate:
    """Simulation-only risk gate for normalized webhook signals."""

    MIN_CONFIDENCE = 50.0
    VALID_ACTIONS = {"BUY", "SELL", "CLOSE", "ALERT_ONLY"}

    def __init__(self, symbol_registry: ClientSymbolRegistry | None = None) -> None:
        self.symbol_registry = symbol_registry or ClientSymbolRegistry()

    def evaluate_signal_risk(self, signal: NormalizedTradingSignal) -> WebhookRiskGateResult:
        reasons: list[str] = []
        warnings: list[str] = []

        if not self.symbol_registry.is_supported(signal.canonical_symbol):
            reasons.append("Unsupported signal symbol.")
        if signal.action not in self.VALID_ACTIONS or signal.action == "INVALID":
            reasons.append("Invalid signal action.")
        if signal.live_execution_enabled:
            reasons.append("Live execution flag must remain disabled.")
        if signal.simulation_only is not True:
            reasons.append("Signal must remain simulation-only.")
        if signal.confidence is None:
            warnings.append("Signal confidence missing; orchestration may require confirmation.")
        elif signal.confidence < self.MIN_CONFIDENCE:
            reasons.append("Signal confidence is below the simulation review threshold.")
        if signal.canonical_symbol == "NIFTY50":
            warnings.append("NIFTY50 broker routing is conditional until Indian broker integration is added.")

        passed = not reasons
        return WebhookRiskGateResult(
            passed=passed,
            risk_level="LOW" if passed and not warnings else "MEDIUM" if passed else "HIGH",
            reasons=reasons,
            warnings=warnings,
        )
