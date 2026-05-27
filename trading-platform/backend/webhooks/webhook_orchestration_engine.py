from backend.webhooks.webhook_broker_routing_preview import WebhookBrokerRoutingPreviewBuilder
from backend.webhooks.webhook_institutional_context_checker import WebhookInstitutionalContextChecker
from backend.webhooks.webhook_models import NormalizedTradingSignal
from backend.webhooks.webhook_orchestration_models import WebhookOrchestrationDecision
from backend.webhooks.webhook_risk_gate import WebhookRiskGate


class WebhookOrchestrationEngine:
    """Bridge normalized TradingView signals into simulation-only orchestration decisions."""

    def __init__(
        self,
        institutional_checker: WebhookInstitutionalContextChecker | None = None,
        risk_gate: WebhookRiskGate | None = None,
        routing_preview_builder: WebhookBrokerRoutingPreviewBuilder | None = None,
    ) -> None:
        self.institutional_checker = institutional_checker or WebhookInstitutionalContextChecker()
        self.risk_gate = risk_gate or WebhookRiskGate()
        self.routing_preview_builder = routing_preview_builder or WebhookBrokerRoutingPreviewBuilder()

    def orchestrate_signal(self, signal: NormalizedTradingSignal) -> WebhookOrchestrationDecision:
        institutional = self.institutional_checker.check_signal_context(signal)
        risk = self.risk_gate.evaluate_signal_risk(signal)
        routing = self.routing_preview_builder.build_preview(signal)

        final_decision = "SIMULATION_ACCEPTED"
        rejection_reasons: list[str] = []
        warnings = list(risk.warnings) + list(institutional.issues)

        if signal.action == "INVALID" or not signal.orchestration_ready:
            final_decision = "INVALID"
            rejection_reasons.append("Signal is invalid or not orchestration-ready.")
        elif not risk.passed:
            final_decision = "BLOCKED"
            rejection_reasons.extend(risk.reasons)
        elif not routing.routing_ready:
            final_decision = "REJECTED"
            rejection_reasons.append(routing.message)
        elif institutional.aligned_with_signal is False:
            final_decision = "WAIT_FOR_CONFIRMATION"
            warnings.append("Institutional context conflicts with the signal direction.")

        explanation = self._explain(final_decision, signal, rejection_reasons, warnings)
        return WebhookOrchestrationDecision(
            signal_id=signal.signal_id,
            canonical_symbol=signal.canonical_symbol,
            action=signal.action,
            institutional_status=institutional,
            risk_status=risk,
            routing_status=routing,
            final_decision=final_decision,
            broker_targets=routing.supported_brokers,
            rejection_reasons=rejection_reasons,
            warnings=warnings,
            explanation=explanation,
            simulation_only=True,
            live_execution_enabled=False,
        )

    def _explain(
        self,
        final_decision: str,
        signal: NormalizedTradingSignal,
        rejection_reasons: list[str],
        warnings: list[str],
    ) -> str:
        if final_decision == "SIMULATION_ACCEPTED":
            return f"{signal.canonical_symbol} {signal.action} signal accepted for simulation-only orchestration review."
        if final_decision == "WAIT_FOR_CONFIRMATION":
            return "Signal is valid, but institutional context asks for confirmation before simulation."
        if final_decision == "BLOCKED":
            return "Signal blocked by risk gate: " + "; ".join(rejection_reasons)
        if final_decision == "REJECTED":
            return "Signal rejected by routing preview: " + "; ".join(rejection_reasons)
        if warnings:
            return "Signal invalid or incomplete; review warnings before simulation."
        return "Signal invalid or not orchestration-ready."
