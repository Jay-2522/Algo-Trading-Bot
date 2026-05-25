from math import isfinite
from typing import Any

from backend.institutional_intelligence.breaker_block_detector import BreakerBlockDetector
from backend.institutional_intelligence.breaker_block_models import BreakerBlock, BreakerBlockValidationResult
from backend.institutional_intelligence.order_block_models import OrderBlock


class BreakerBlockValidator:
    """Verify source invalidation, displacement, and directional structure shift."""

    def __init__(self, detector: BreakerBlockDetector | None = None) -> None:
        self.detector = detector or BreakerBlockDetector()

    def validate_breaker_block(
        self,
        breaker_block: BreakerBlock,
        candles: list[Any] | None,
        source_order_block: OrderBlock | None,
    ) -> BreakerBlockValidationResult:
        if source_order_block is None or source_order_block.ob_id != breaker_block.source_order_block_id:
            return self._invalid("Referenced source order block is unavailable.")
        if not source_order_block.valid:
            return self._invalid("Breaker source order block was not previously valid.")
        if breaker_block.original_ob_direction != source_order_block.direction:
            return self._invalid("Breaker original direction does not match its source order block.")
        expected_direction = "BULLISH" if source_order_block.direction == "BEARISH" else "BEARISH"
        if breaker_block.direction != expected_direction:
            return self._invalid("Breaker direction does not represent an order block failure.")
        if (
            not candles
            or breaker_block.candle_index <= source_order_block.candle_index
            or breaker_block.zone_high <= breaker_block.zone_low
        ):
            return self._invalid("Breaker zone or formation sequence is invalid.")
        values = self._values(candles[breaker_block.candle_index]) if breaker_block.candle_index < len(candles) else None
        if values is None:
            return self._invalid("Breaker invalidation candle contains malformed OHLC data.")
        if breaker_block.direction == "BULLISH":
            boundary_closed = values["close"] > source_order_block.zone_high
        else:
            boundary_closed = values["close"] < source_order_block.zone_low
        if not boundary_closed:
            return self._invalid("Price did not close beyond the failed order block boundary.")
        redetected = self.detector.detect_breaker_block(
            candles,
            source_order_block,
            breaker_block.symbol,
            breaker_block.timeframe,
        )
        if redetected is None or redetected.candle_index != breaker_block.candle_index:
            return self._invalid("No qualifying displacement candle confirms the order block invalidation.")
        return BreakerBlockValidationResult(
            valid=True,
            validation_reason="Valid source order block failed on a displacement close beyond its boundary, confirming structure shift.",
            validation_confidence=100.0,
        )

    def _invalid(self, reason: str) -> BreakerBlockValidationResult:
        return BreakerBlockValidationResult(valid=False, validation_reason=reason, validation_confidence=0.0)

    def _values(self, candle: Any) -> dict | None:
        try:
            getter = candle.get if isinstance(candle, dict) else lambda field: getattr(candle, field)
            values = {field: float(getter(field)) for field in ("open", "high", "low", "close")}
            if not all(isfinite(value) for value in values.values()) or values["high"] < values["low"]:
                return None
            return values
        except (AttributeError, KeyError, TypeError, ValueError):
            return None
