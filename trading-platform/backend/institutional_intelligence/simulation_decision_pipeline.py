from typing import Any

from backend.institutional_intelligence.simulation_decision_explainer import SimulationDecisionExplainer
from backend.institutional_intelligence.simulation_decision_models import InstitutionalSimulationDecision
from backend.institutional_intelligence.simulation_intent_builder import SimulationIntentBuilder
from backend.institutional_intelligence.setup_validator_models import SetupValidationContext, SetupValidationResult


class InstitutionalSimulationDecisionPipeline:
    """Convert validated setups into simulation eligibility and analytical intent only."""

    def __init__(
        self,
        intent_builder: SimulationIntentBuilder | None = None,
        explainer: SimulationDecisionExplainer | None = None,
    ) -> None:
        self.intent_builder = intent_builder or SimulationIntentBuilder()
        self.explainer = explainer or SimulationDecisionExplainer()

    def generate_decision(
        self,
        validation_context: SetupValidationContext,
        risk_status: Any = None,
        news_status: Any = None,
        session_context: Any = None,
    ) -> tuple[SetupValidationResult | None, InstitutionalSimulationDecision]:
        selected = self._select(validation_context)
        global_blocks = self._blocks(risk_status, news_status, session_context)
        critical = [
            reason
            for result in validation_context.rejected_setups
            for reason in result.rejection_reasons
        ]
        approved = selected is not None and selected in validation_context.approved_setups
        conditional = selected is not None and selected in validation_context.waiting_setups
        intent = self.intent_builder.build_order_intent(selected)
        if global_blocks:
            action, readiness = "AVOID", "BLOCKED"
            allowed = False
            intent = self._none_intent(validation_context, intent)
        elif approved and intent.risk_quality in {"EXCELLENT", "GOOD", "ACCEPTABLE"}:
            action = "SIMULATE_BUY" if selected.direction == "BULLISH" else "SIMULATE_SELL"
            readiness = "APPROVED_FOR_SIMULATION"
            allowed = True
        elif approved:
            action, readiness, allowed = "AVOID", "BLOCKED", False
            global_blocks.append("Approved setup has unacceptable simulation risk geometry.")
            intent = self._none_intent(validation_context, intent)
        elif conditional:
            action, readiness, allowed = "WAIT", "WAIT_FOR_CONFIRMATION", False
        elif critical:
            action, readiness, allowed = "AVOID", "BLOCKED", False
            intent = self._none_intent(validation_context, intent)
        else:
            action, readiness, allowed = "NO_TRADE", "NO_VALID_SETUP", False
            intent = self._none_intent(validation_context, intent)
        decision = InstitutionalSimulationDecision(
            symbol=validation_context.symbol,
            timeframe=validation_context.timeframe,
            action=action,
            approved_for_simulation=allowed,
            readiness=readiness,
            confidence=selected.confidence if selected else 0.0,
            setup_quality=self._grade(validation_context, selected),
            selected_model_type=selected.model_type if selected else None,
            order_intent=intent,
            approval_reasons=selected.approval_reasons if allowed and selected else [],
            rejection_reasons=list(dict.fromkeys([*global_blocks, *critical])),
            warnings=selected.warnings if selected else [],
        )
        detail = self.explainer.explain_decision(decision)
        return selected, decision.model_copy(update={"explanation": str(detail["summary"])})

    def _none_intent(self, context: SetupValidationContext, source_intent: Any) -> Any:
        return source_intent.model_copy(
            update={
                "symbol": context.symbol,
                "timeframe": context.timeframe,
                "direction": "NONE",
                "entry_low": None,
                "entry_high": None,
                "invalidation_level": None,
                "target_level": None,
                "estimated_rr": 0.0,
                "risk_quality": "INVALID",
            }
        )

    def _select(self, context: SetupValidationContext) -> SetupValidationResult | None:
        available = context.approved_setups or context.waiting_setups
        return max(available, key=lambda result: result.overall_score, default=None)

    def _blocks(self, risk: Any, news: Any, session: Any) -> list[str]:
        reasons = []
        if self._get(risk, "overall_status") == "BLOCKED":
            reasons.append("Risk status blocks simulation intent.")
        if self._get(news, "active_blackout") or self._get(news, "trading_allowed") is False:
            reasons.append("News blackout blocks simulation intent.")
        if self._get(session, "trade_timing_readiness") in {"AVOID_NEWS_WINDOW", "AVOID_LOW_LIQUIDITY"}:
            reasons.append("Session readiness blocks simulation intent.")
        return reasons

    def _grade(self, context: SetupValidationContext, selected: SetupValidationResult | None) -> str:
        if selected is None:
            return "REJECTED"
        for index, result in enumerate(context.validations):
            if result.validation_id == selected.validation_id and index < len(context.decisions):
                return context.decisions[index].approval_grade
        return "REJECTED"

    def _get(self, value: Any, key: str) -> Any:
        if value is None:
            return None
        return value.get(key) if isinstance(value, dict) else getattr(value, key, None)
