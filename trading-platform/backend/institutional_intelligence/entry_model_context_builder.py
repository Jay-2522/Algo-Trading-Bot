from typing import Any

from backend.institutional_intelligence.breaker_block_models import BreakerBlockContext
from backend.institutional_intelligence.confluence_context_builder import ConfluenceContextBuilder
from backend.institutional_intelligence.confluence_models import ConfluenceContext, InstitutionalConfluenceScore
from backend.institutional_intelligence.entry_model_detector import EntryModelDetector
from backend.institutional_intelligence.entry_model_explainer import EntryModelExplainer
from backend.institutional_intelligence.entry_model_models import EntryModelContext
from backend.institutional_intelligence.entry_model_scorer import EntryModelScorer
from backend.institutional_intelligence.entry_model_validator import EntryModelValidator
from backend.institutional_intelligence.fair_value_gap_models import FVGContext
from backend.institutional_intelligence.liquidity_sweep_models import SweepContext
from backend.institutional_intelligence.order_block_models import OrderBlockContext
from backend.institutional_intelligence.session_context_builder import SessionContextBuilder
from backend.institutional_intelligence.smc_models import InstitutionalContext
from backend.institutional_intelligence.structure_shift_models import StructureShiftContext


class EntryModelContextBuilder:
    """Orchestrate institutional evidence into ranked analysis-only setup models."""

    def __init__(
        self,
        confluence_builder: ConfluenceContextBuilder | None = None,
        session_builder: SessionContextBuilder | None = None,
        detector: EntryModelDetector | None = None,
        validator: EntryModelValidator | None = None,
        scorer: EntryModelScorer | None = None,
        explainer: EntryModelExplainer | None = None,
    ) -> None:
        self.confluence_builder = confluence_builder or ConfluenceContextBuilder()
        self.session_builder = session_builder or SessionContextBuilder()
        self.detector = detector or EntryModelDetector()
        self.validator = validator or EntryModelValidator()
        self.scorer = scorer or EntryModelScorer()
        self.explainer = explainer or EntryModelExplainer()

    def build_entry_model_context(
        self,
        symbol: str,
        timeframe: str,
        candles: list[Any] | None,
        confluence_context: ConfluenceContext | None = None,
        alignment_context: Any = None,
        session_context: Any = None,
        news_status: Any = None,
    ) -> EntryModelContext:
        normalized_symbol = symbol.strip().upper()
        normalized_timeframe = timeframe.strip().upper()
        source = candles or []
        confluence = confluence_context or self._safe_confluence(normalized_symbol, normalized_timeframe, source)
        session = session_context or self.session_builder.build_session_context(
            normalized_symbol,
            normalized_timeframe,
            source,
            sweep_context=confluence.sweep_context,
            news_status=news_status,
            confluence_context=confluence,
            alignment_context=alignment_context,
        )
        detected = self.detector.detect_entry_models(
            normalized_symbol,
            normalized_timeframe,
            sweep_context=confluence.sweep_context,
            fvg_context=confluence.fvg_context,
            order_block_context=confluence.order_block_context,
            breaker_context=confluence.breaker_context,
            structure_shift_context=confluence.structure_shift_context,
            confluence_context=confluence,
            alignment_context=alignment_context,
            session_context=session,
        )
        assessed = []
        for model in detected:
            validation = self.validator.validate_model(model, confluence, alignment_context, session)
            scored = self.scorer.score_model(model, confluence, alignment_context, session)
            updated = model.model_copy(
                update={
                    "readiness": validation.readiness,
                    "confidence": 0.0
                    if model.model_type == "NO_TRADE"
                    else round((validation.confidence + scored.score) / 2.0, 2),
                    "quality_score": scored.score,
                    "blocking_factors": list(dict.fromkeys([*model.blocking_factors, *validation.blocking_factors])),
                    "warnings": list(dict.fromkeys([*model.warnings, *validation.missing_requirements])),
                    "metadata": {
                        **model.metadata,
                        "valid": validation.valid,
                        "validation_reason": validation.reason,
                        "score_breakdown": scored.model_dump(mode="json"),
                    },
                }
            )
            explanation = self.explainer.explain_model(updated)
            assessed.append(updated.model_copy(update={"metadata": {**updated.metadata, "explanation": explanation}}))
        actionable = [model for model in assessed if model.model_type != "NO_TRADE"]
        best = max(actionable or assessed, key=lambda model: model.quality_score, default=None)
        ready = [model for model in actionable if model.readiness == "READY_FOR_SIMULATION"]
        waiting = [model for model in actionable if model.readiness == "WAIT_FOR_CONFIRMATION"]
        avoided = [model for model in assessed if model.readiness == "AVOID" or model.model_type == "NO_TRADE"]
        readiness = self._readiness(ready, waiting, assessed)
        quality_set = actionable if actionable else []
        confidence = round(sum(model.confidence for model in quality_set) / len(quality_set), 2) if quality_set else 0.0
        return EntryModelContext(
            symbol=normalized_symbol,
            timeframe=normalized_timeframe,
            models=assessed,
            best_model=best,
            bullish_models=[model for model in actionable if model.direction == "BULLISH"],
            bearish_models=[model for model in actionable if model.direction == "BEARISH"],
            ready_models=ready,
            waiting_models=waiting,
            avoided_models=avoided,
            overall_readiness=readiness,
            confidence=confidence,
        )

    def _readiness(self, ready: list, waiting: list, all_models: list) -> str:
        if ready:
            return "READY_FOR_SIMULATION"
        if waiting:
            return "WAIT_FOR_CONFIRMATION"
        if any(model.readiness == "AVOID" for model in all_models):
            return "AVOID"
        return "NO_SETUP"

    def _safe_confluence(self, symbol: str, timeframe: str, candles: list[Any]) -> ConfluenceContext:
        try:
            return self.confluence_builder.build_confluence_context(symbol, timeframe, candles)
        except Exception:
            return ConfluenceContext(
                symbol=symbol,
                timeframe=timeframe,
                institutional_context=InstitutionalContext(symbol=symbol, timeframe=timeframe),
                sweep_context=SweepContext(symbol=symbol, timeframe=timeframe),
                fvg_context=FVGContext(symbol=symbol, timeframe=timeframe),
                order_block_context=OrderBlockContext(symbol=symbol, timeframe=timeframe),
                breaker_context=BreakerBlockContext(symbol=symbol, timeframe=timeframe),
                structure_shift_context=StructureShiftContext(symbol=symbol, timeframe=timeframe),
                confluence_score=InstitutionalConfluenceScore(symbol=symbol, timeframe=timeframe),
            )
