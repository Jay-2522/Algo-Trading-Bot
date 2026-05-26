from typing import Any

from backend.institutional_intelligence.simulation_decision_models import SimulationDecisionContext
from backend.institutional_intelligence.simulation_decision_pipeline import InstitutionalSimulationDecisionPipeline
from backend.institutional_intelligence.setup_validation_context_builder import SetupValidationContextBuilder
from backend.institutional_intelligence.setup_validator_models import SetupValidationContext


class SimulationDecisionContextBuilder:
    """Build a safe final decision from validated institutional simulation candidates."""

    def __init__(
        self,
        validation_builder: SetupValidationContextBuilder | None = None,
        pipeline: InstitutionalSimulationDecisionPipeline | None = None,
    ) -> None:
        self.validation_builder = validation_builder or SetupValidationContextBuilder()
        self.pipeline = pipeline or InstitutionalSimulationDecisionPipeline()

    def build_simulation_decision_context(
        self,
        symbol: str,
        timeframe: str,
        candles: list[Any] | None,
        validation_context: SetupValidationContext | None = None,
        risk_status: Any = None,
        news_status: Any = None,
        session_context: Any = None,
    ) -> SimulationDecisionContext:
        normalized_symbol = symbol.strip().upper()
        normalized_timeframe = timeframe.strip().upper()
        validation = validation_context or self.validation_builder.build_validation_context(
            normalized_symbol,
            normalized_timeframe,
            candles,
            risk_context=risk_status,
            news_status=news_status,
            session_context=session_context,
        )
        selected, decision = self.pipeline.generate_decision(
            validation,
            risk_status=risk_status,
            news_status=news_status,
            session_context=session_context,
        )
        return SimulationDecisionContext(
            symbol=normalized_symbol,
            timeframe=normalized_timeframe,
            validation_context=validation,
            selected_validation=selected,
            decision=decision,
        )
