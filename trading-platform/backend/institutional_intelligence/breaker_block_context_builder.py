from typing import Any

from backend.institutional_intelligence.breaker_block_detector import BreakerBlockDetector
from backend.institutional_intelligence.breaker_block_mitigation_tracker import BreakerBlockMitigationTracker
from backend.institutional_intelligence.breaker_block_models import BreakerBlockContext
from backend.institutional_intelligence.breaker_block_strength_scorer import BreakerBlockStrengthScorer
from backend.institutional_intelligence.breaker_block_validator import BreakerBlockValidator
from backend.institutional_intelligence.order_block_models import OrderBlockContext


class BreakerBlockContextBuilder:
    """Build dashboard-ready breaker lifecycle context from failed valid OBs."""

    HIGH_QUALITY_THRESHOLD = 75.0

    def __init__(
        self,
        detector: BreakerBlockDetector | None = None,
        validator: BreakerBlockValidator | None = None,
        mitigation_tracker: BreakerBlockMitigationTracker | None = None,
        scorer: BreakerBlockStrengthScorer | None = None,
    ) -> None:
        self.detector = detector or BreakerBlockDetector()
        self.validator = validator or BreakerBlockValidator(self.detector)
        self.mitigation_tracker = mitigation_tracker or BreakerBlockMitigationTracker()
        self.scorer = scorer or BreakerBlockStrengthScorer()

    def build_breaker_context(
        self,
        symbol: str,
        timeframe: str,
        candles: list[Any] | None,
        order_block_context: OrderBlockContext | None = None,
        fvg_context: Any = None,
        sweep_context: Any = None,
        structure_bias: Any = None,
    ) -> BreakerBlockContext:
        normalized_symbol = symbol.strip().upper()
        normalized_timeframe = timeframe.strip().upper()
        source = candles or []
        order_blocks = order_block_context.order_blocks if order_block_context is not None else []
        by_id = {order_block.ob_id: order_block for order_block in order_blocks}
        breakers = []
        for detected in self.detector.detect_breaker_blocks(source, order_blocks, normalized_symbol, normalized_timeframe):
            source_ob = by_id.get(detected.source_order_block_id)
            validation = self.validator.validate_breaker_block(detected, source, source_ob)
            lifecycle = self.mitigation_tracker.update_breaker_mitigation(
                detected,
                source[detected.candle_index + 1 :],
            )
            assessed = lifecycle.model_copy(
                update={
                    "valid": validation.valid,
                    "structure_shift_confirmed": validation.valid and detected.structure_shift_confirmed,
                    "related_fvg": self.scorer.find_related_fvg(lifecycle, fvg_context),
                    "related_sweep": self.scorer.find_related_sweep(lifecycle, sweep_context),
                    "structure_bias": self._bias(structure_bias),
                    "metadata": {
                        **lifecycle.metadata,
                        "validation_reason": validation.validation_reason,
                        "validation_confidence": validation.validation_confidence,
                    },
                }
            )
            score = self.scorer.score_breaker_block(
                assessed,
                fvg_context=fvg_context,
                sweep_context=sweep_context,
                structure_bias=structure_bias,
            )
            breakers.append(
                assessed.model_copy(
                    update={
                        "strength": score.score,
                        "metadata": {
                            **assessed.metadata,
                            "strength_breakdown": score.model_dump(mode="json"),
                        },
                    }
                )
            )
        valid = [breaker for breaker in breakers if breaker.valid]
        return BreakerBlockContext(
            symbol=normalized_symbol,
            timeframe=normalized_timeframe,
            breaker_blocks=breakers,
            fresh_breakers=[breaker for breaker in valid if breaker.mitigation_status == "FRESH"],
            mitigated_breakers=[breaker for breaker in valid if breaker.mitigation_status != "FRESH"],
            high_quality_breakers=[
                breaker for breaker in valid if breaker.strength >= self.HIGH_QUALITY_THRESHOLD
            ],
            latest_breaker=valid[-1] if valid else None,
            confidence=round(sum(breaker.strength for breaker in valid) / len(valid), 2) if valid else 0.0,
        )

    def _bias(self, context: Any) -> str | None:
        if context is None:
            return None
        if isinstance(context, str):
            return context
        return context.get("bias") if isinstance(context, dict) else getattr(context, "bias", None)
