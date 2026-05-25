from typing import Any

from backend.institutional_intelligence.order_block_detector import OrderBlockDetector
from backend.institutional_intelligence.order_block_mitigation_tracker import OrderBlockMitigationTracker
from backend.institutional_intelligence.order_block_models import OrderBlockContext
from backend.institutional_intelligence.order_block_strength_scorer import OrderBlockStrengthScorer
from backend.institutional_intelligence.order_block_validator import OrderBlockValidator


class OrderBlockContextBuilder:
    """Aggregate validated order blocks, lifecycle status, and confluence context."""

    HIGH_QUALITY_THRESHOLD = 75.0

    def __init__(
        self,
        detector: OrderBlockDetector | None = None,
        validator: OrderBlockValidator | None = None,
        mitigation_tracker: OrderBlockMitigationTracker | None = None,
        scorer: OrderBlockStrengthScorer | None = None,
    ) -> None:
        self.detector = detector or OrderBlockDetector()
        self.validator = validator or OrderBlockValidator(self.detector)
        self.mitigation_tracker = mitigation_tracker or OrderBlockMitigationTracker()
        self.scorer = scorer or OrderBlockStrengthScorer()

    def build_order_block_context(
        self,
        symbol: str,
        timeframe: str,
        candles: list[Any] | None,
        fvg_context: Any = None,
        sweep_context: Any = None,
        structure_bias: Any = None,
    ) -> OrderBlockContext:
        normalized_symbol = symbol.strip().upper()
        normalized_timeframe = timeframe.strip().upper()
        source = candles or []
        order_blocks = []
        for detected in self.detector.detect_order_blocks(source, normalized_symbol, normalized_timeframe):
            validation = self.validator.validate_order_block(detected, source)
            displacement_index = int(detected.metadata.get("displacement_index", detected.candle_index))
            lifecycle = self.mitigation_tracker.update_order_block_mitigation(
                detected,
                source[displacement_index + 1 :],
            )
            assessed = lifecycle.model_copy(
                update={
                    "displacement_confirmed": validation.displacement_confirmed,
                    "bos_confirmed": validation.bos_confirmed,
                    "valid": validation.valid,
                    "related_fvg": self.scorer.find_related_fvg(lifecycle, fvg_context),
                    "related_sweep": self.scorer.find_related_sweep(lifecycle, sweep_context),
                    "structure_bias": self._bias(structure_bias),
                    "metadata": {
                        **lifecycle.metadata,
                        "validation_reason": validation.reason,
                        "validation_confidence": validation.confidence,
                    },
                }
            )
            score = self.scorer.score_order_block(
                assessed,
                source,
                fvg_context=fvg_context,
                sweep_context=sweep_context,
                structure_bias=structure_bias,
            )
            order_blocks.append(
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
        valid = [order_block for order_block in order_blocks if order_block.valid]
        return OrderBlockContext(
            symbol=normalized_symbol,
            timeframe=normalized_timeframe,
            order_blocks=order_blocks,
            fresh_order_blocks=[ob for ob in valid if ob.mitigation_status == "FRESH"],
            mitigated_order_blocks=[ob for ob in valid if ob.mitigation_status != "FRESH"],
            high_quality_order_blocks=[ob for ob in valid if ob.strength >= self.HIGH_QUALITY_THRESHOLD],
            latest_order_block=valid[-1] if valid else None,
            bullish_order_blocks=[ob for ob in valid if ob.direction == "BULLISH"],
            bearish_order_blocks=[ob for ob in valid if ob.direction == "BEARISH"],
            confidence=round(sum(ob.strength for ob in valid) / len(valid), 2) if valid else 0.0,
        )

    def _bias(self, context: Any) -> str | None:
        if context is None:
            return None
        if isinstance(context, str):
            return context
        return context.get("bias") if isinstance(context, dict) else getattr(context, "bias", None)
