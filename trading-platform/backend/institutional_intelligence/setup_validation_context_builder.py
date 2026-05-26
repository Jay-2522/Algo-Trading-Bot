from typing import Any

from backend.institutional_intelligence.entry_model_context_builder import EntryModelContextBuilder
from backend.institutional_intelligence.entry_model_models import EntryModelContext
from backend.institutional_intelligence.setup_approval_engine import SetupApprovalEngine
from backend.institutional_intelligence.setup_validator_engine import SetupValidatorEngine
from backend.institutional_intelligence.setup_validator_models import SetupValidationContext


class SetupValidationContextBuilder:
    """Validate and approve institutional candidates for simulation eligibility only."""

    def __init__(
        self,
        entry_model_builder: EntryModelContextBuilder | None = None,
        validator: SetupValidatorEngine | None = None,
        approval_engine: SetupApprovalEngine | None = None,
    ) -> None:
        self.entry_model_builder = entry_model_builder or EntryModelContextBuilder()
        self.validator = validator or SetupValidatorEngine()
        self.approval_engine = approval_engine or SetupApprovalEngine()

    def build_validation_context(
        self,
        symbol: str,
        timeframe: str,
        candles: list[Any] | None,
        entry_model_context: EntryModelContext | None = None,
        confluence_context: Any = None,
        alignment_context: Any = None,
        session_context: Any = None,
        risk_context: Any = None,
        news_status: Any = None,
    ) -> SetupValidationContext:
        normalized_symbol = symbol.strip().upper()
        normalized_timeframe = timeframe.strip().upper()
        entries = entry_model_context or self.entry_model_builder.build_entry_model_context(
            normalized_symbol,
            normalized_timeframe,
            candles,
            confluence_context=confluence_context,
            alignment_context=alignment_context,
            session_context=session_context,
            news_status=news_status,
        )
        validations = [
            self.validator.validate_setup(
                model,
                confluence_context=confluence_context,
                alignment_context=alignment_context,
                session_context=session_context,
                risk_context=risk_context,
            )
            for model in entries.models
        ]
        decisions = [self.approval_engine.generate_decision(result) for result in validations]
        paired = list(zip(validations, decisions))
        approved = [result for result, decision in paired if decision.simulation_eligible]
        waiting = [
            result for result, decision in paired
            if not decision.simulation_eligible and decision.execution_readiness in {"CONDITIONAL", "WAIT"}
        ]
        rejected = [result for result, decision in paired if decision.execution_readiness == "REJECTED"]
        best_pair = max(paired, key=lambda item: item[0].overall_score, default=(None, None))
        if approved:
            readiness = "APPROVED"
        elif waiting:
            readiness = "CONDITIONAL" if any(
                decision.execution_readiness == "CONDITIONAL" for _, decision in paired
            ) else "WAIT"
        else:
            readiness = "REJECTED"
        confidence_source = approved or waiting
        confidence = (
            round(sum(result.confidence for result in confidence_source) / len(confidence_source), 2)
            if confidence_source
            else 0.0
        )
        return SetupValidationContext(
            symbol=normalized_symbol,
            timeframe=normalized_timeframe,
            validations=validations,
            decisions=decisions,
            approved_setups=approved,
            waiting_setups=waiting,
            rejected_setups=rejected,
            best_setup=best_pair[0],
            best_decision=best_pair[1],
            simulation_eligible=bool(approved),
            execution_readiness=readiness,
            confidence=confidence,
        )
