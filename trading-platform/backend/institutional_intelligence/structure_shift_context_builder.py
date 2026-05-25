from typing import Any

from backend.institutional_intelligence.smc_models import SwingPoint
from backend.institutional_intelligence.structure_shift_detector import StructureShiftDetector
from backend.institutional_intelligence.structure_shift_models import StructureShiftContext
from backend.institutional_intelligence.structure_shift_strength_scorer import StructureShiftStrengthScorer
from backend.institutional_intelligence.structure_shift_validator import StructureShiftValidator
from backend.institutional_intelligence.swing_detector import SwingDetector


class StructureShiftContextBuilder:
    """Aggregate validated BOS, CHOCH, and MSS events for analysis dashboards."""

    HIGH_QUALITY_THRESHOLD = 75.0

    def __init__(
        self,
        swing_detector: SwingDetector | None = None,
        detector: StructureShiftDetector | None = None,
        validator: StructureShiftValidator | None = None,
        scorer: StructureShiftStrengthScorer | None = None,
    ) -> None:
        self.swing_detector = swing_detector or SwingDetector()
        self.detector = detector or StructureShiftDetector()
        self.validator = validator or StructureShiftValidator()
        self.scorer = scorer or StructureShiftStrengthScorer()

    def build_structure_shift_context(
        self,
        symbol: str,
        timeframe: str,
        candles: list[Any] | None,
        swings: list[SwingPoint] | None = None,
        sweep_context: Any = None,
        fvg_context: Any = None,
        ob_context: Any = None,
        breaker_context: Any = None,
        structure_bias: Any = None,
    ) -> StructureShiftContext:
        normalized_symbol = symbol.strip().upper()
        normalized_timeframe = timeframe.strip().upper()
        source = candles or []
        swing_points = swings if swings is not None else self.swing_detector.detect_swings(source)
        assessed = []
        for event in self.detector.detect_structure_events(
            source,
            swing_points,
            normalized_symbol,
            normalized_timeframe,
            prior_bias=None,
        ):
            validation = self.validator.validate_event(event, source, swing_points)
            enriched = event.model_copy(
                update={
                    "valid": validation.valid,
                    "close_confirmed": validation.close_confirmed,
                    "wick_break": validation.wick_break,
                    "related_sweep": self.scorer.find_related_sweep(event, sweep_context),
                    "related_fvg": self.scorer.find_related_fvg(event, fvg_context),
                    "related_order_block": self.scorer.find_related_order_block(event, ob_context),
                    "related_breaker": self.scorer.find_related_breaker(event, breaker_context),
                    "metadata": {
                        **event.metadata,
                        "validation_reason": validation.reason,
                        "validation_break_strength": validation.break_strength,
                        "structure_bias": self._bias(structure_bias),
                    },
                }
            )
            score = self.scorer.score_event(
                enriched,
                source,
                swing_points,
                sweep_context=sweep_context,
                fvg_context=fvg_context,
                ob_context=ob_context,
                breaker_context=breaker_context,
                structure_bias=structure_bias,
            )
            assessed.append(
                enriched.model_copy(
                    update={
                        "strength": score.score,
                        "metadata": {
                            **enriched.metadata,
                            "strength_breakdown": score.model_dump(mode="json"),
                        },
                    }
                )
            )
        valid = [event for event in assessed if event.valid]
        return StructureShiftContext(
            symbol=normalized_symbol,
            timeframe=normalized_timeframe,
            events=assessed,
            bos_events=[event for event in valid if event.event_type == "BOS"],
            choch_events=[event for event in valid if event.event_type == "CHOCH"],
            mss_events=[event for event in valid if event.event_type == "MSS"],
            latest_event=valid[-1] if valid else None,
            bullish_events=[event for event in valid if event.direction == "BULLISH"],
            bearish_events=[event for event in valid if event.direction == "BEARISH"],
            high_quality_events=[event for event in valid if event.strength >= self.HIGH_QUALITY_THRESHOLD],
            current_structure_state=self._state(valid, structure_bias),
            confidence=round(sum(event.strength for event in valid) / len(valid), 2) if valid else 0.0,
        )

    def _state(self, events: list, structure_bias: Any) -> str:
        if not events:
            bias = self._bias(structure_bias)
            return bias if bias in {"BULLISH", "BEARISH", "RANGING"} else "UNCLEAR"
        latest = events[-1]
        if latest.event_type == "CHOCH":
            return "TRANSITIONING"
        return latest.direction

    def _bias(self, context: Any) -> str | None:
        if isinstance(context, str):
            return context
        if isinstance(context, dict):
            return context.get("bias")
        return getattr(context, "bias", None)
