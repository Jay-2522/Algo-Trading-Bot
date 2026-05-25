from math import isfinite
from typing import Any

from backend.institutional_intelligence.order_block_detector import OrderBlockDetector
from backend.institutional_intelligence.order_block_models import OrderBlock, OrderBlockValidationResult


class OrderBlockValidator:
    """Require deterministic impulse and break-of-structure confirmation."""

    STRUCTURE_LOOKBACK = 5

    def __init__(self, detector: OrderBlockDetector | None = None) -> None:
        self.detector = detector or OrderBlockDetector()

    def validate_order_block(
        self,
        order_block: OrderBlock,
        candles: list[Any] | None,
    ) -> OrderBlockValidationResult:
        if order_block.direction not in {"BULLISH", "BEARISH"}:
            return self._invalid("Unsupported order block direction.")
        if not self._valid_zone(order_block):
            return self._invalid("Order block candle or zone contains invalid OHLC values.")
        if not candles or order_block.candle_index >= len(candles):
            return self._invalid("No source candles are available for validation.")
        redetected = (
            self.detector.detect_bullish_order_block(candles, order_block.candle_index, order_block.symbol, order_block.timeframe)
            if order_block.direction == "BULLISH"
            else self.detector.detect_bearish_order_block(candles, order_block.candle_index, order_block.symbol, order_block.timeframe)
        )
        if redetected is None:
            return self._invalid("No qualifying displacement occurred after the order block candle.")
        displacement_index = int(redetected.metadata["displacement_index"])
        prior = [
            self._values(candle)
            for candle in candles[
                max(0, order_block.candle_index - self.STRUCTURE_LOOKBACK) : order_block.candle_index
            ]
        ]
        structural_reference = [value for value in prior if value is not None]
        if not structural_reference:
            return OrderBlockValidationResult(
                valid=False,
                displacement_confirmed=True,
                bos_confirmed=False,
                reason="Displacement confirmed, but no valid preceding structure exists for BOS validation.",
                confidence=50.0,
            )
        future = [
            self._values(candle)
            for candle in candles[displacement_index:]
        ]
        evaluable_future = [value for value in future if value is not None]
        if order_block.direction == "BULLISH":
            level = max(value["high"] for value in structural_reference)
            bos_confirmed = any(value["high"] > level and value["close"] > level for value in evaluable_future)
        else:
            level = min(value["low"] for value in structural_reference)
            bos_confirmed = any(value["low"] < level and value["close"] < level for value in evaluable_future)
        if not bos_confirmed:
            return OrderBlockValidationResult(
                valid=False,
                displacement_confirmed=True,
                bos_confirmed=False,
                reason="Displacement confirmed without a closing break of preceding structure.",
                confidence=50.0,
            )
        return OrderBlockValidationResult(
            valid=True,
            displacement_confirmed=True,
            bos_confirmed=True,
            reason="Opposing candle preceded displacement that closed through preceding structure.",
            confidence=100.0,
        )

    def _invalid(self, reason: str) -> OrderBlockValidationResult:
        return OrderBlockValidationResult(
            valid=False,
            displacement_confirmed=False,
            bos_confirmed=False,
            reason=reason,
            confidence=0.0,
        )

    def _valid_zone(self, order_block: OrderBlock) -> bool:
        values = [
            order_block.open,
            order_block.high,
            order_block.low,
            order_block.close,
            order_block.zone_high,
            order_block.zone_low,
        ]
        return (
            all(isfinite(value) for value in values)
            and order_block.high >= order_block.low
            and order_block.zone_high > order_block.zone_low
            and order_block.zone_high == order_block.high
            and order_block.zone_low == order_block.low
        )

    def _values(self, candle: Any) -> dict | None:
        try:
            getter = candle.get if isinstance(candle, dict) else lambda field: getattr(candle, field)
            values = {field: float(getter(field)) for field in ("open", "high", "low", "close")}
            if not all(isfinite(value) for value in values.values()):
                return None
            if values["high"] < values["low"]:
                return None
            return values
        except (AttributeError, KeyError, TypeError, ValueError):
            return None
