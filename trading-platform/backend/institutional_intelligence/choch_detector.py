from datetime import datetime, timezone
from math import isfinite
from typing import Any

from backend.institutional_intelligence.smc_models import SwingPoint
from backend.institutional_intelligence.structure_shift_models import StructureEvent


class CHOCHDetector:
    """Detect counter-structure swing failures indicating possible reversal."""

    def detect_choch(
        self,
        candles: list[Any] | None,
        swings: list[SwingPoint] | None,
        symbol: str,
        timeframe: str,
        prior_bias: Any = None,
    ) -> list[StructureEvent]:
        bias = self._bias(prior_bias)
        allowed = (
            {"BULLISH"} if bias == "BEARISH"
            else {"BEARISH"} if bias == "BULLISH"
            else {"BULLISH", "BEARISH"} if bias in {"RANGING", "UNCLEAR", None}
            else set()
        )
        if not candles or not swings or not allowed:
            return []
        events = []
        consumed: set[tuple[str, float]] = set()
        for swing in sorted(swings, key=lambda item: item.index):
            direction = "BULLISH" if swing.type == "HIGH" else "BEARISH"
            if direction not in allowed or not self._is_counter_reference(swings, swing, direction):
                continue
            key = (direction, swing.price)
            if key in consumed:
                continue
            broken = self._first_break(candles, swing, direction)
            if broken is None:
                continue
            index, values, close_confirmed = broken
            events.append(
                StructureEvent(
                    symbol=symbol.strip().upper(),
                    timeframe=timeframe.strip().upper(),
                    event_type="CHOCH",
                    direction=direction,
                    break_level=swing.price,
                    break_price=round(values["close"] if close_confirmed else values["high" if direction == "BULLISH" else "low"], 5),
                    candle_index=index,
                    timestamp=values["timestamp"],
                    swing_reference=swing.model_dump(mode="json"),
                    close_confirmed=close_confirmed,
                    wick_break=not close_confirmed,
                    continuation=False,
                    reversal=True,
                    metadata={"prior_bias": bias, "break_class": "STRONG" if close_confirmed else "WEAK"},
                )
            )
            consumed.add(key)
        return events

    def _is_counter_reference(self, swings: list[SwingPoint], swing: SwingPoint, direction: str) -> bool:
        prior = [item for item in swings if item.type == swing.type and item.index < swing.index]
        if not prior:
            return False
        previous = prior[-1]
        return swing.price < previous.price if direction == "BULLISH" else swing.price > previous.price

    def _first_break(self, candles: list[Any], swing: SwingPoint, direction: str) -> tuple[int, dict, bool] | None:
        for index in range(swing.index + 1, len(candles)):
            values = self._values(candles[index])
            if values is None:
                continue
            close_break = values["close"] > swing.price if direction == "BULLISH" else values["close"] < swing.price
            wick_break = values["high"] > swing.price if direction == "BULLISH" else values["low"] < swing.price
            if close_break or wick_break:
                return index, values, close_break
        return None

    def _bias(self, prior_bias: Any) -> str | None:
        if isinstance(prior_bias, str):
            return prior_bias
        if isinstance(prior_bias, dict):
            return prior_bias.get("bias")
        return getattr(prior_bias, "bias", None)

    def _values(self, candle: Any) -> dict | None:
        try:
            getter = candle.get if isinstance(candle, dict) else lambda field: getattr(candle, field)
            values = {field: float(getter(field)) for field in ("open", "high", "low", "close")}
            if not all(isfinite(value) for value in values.values()) or values["high"] < values["low"]:
                return None
            timestamp = candle.get("time", candle.get("timestamp")) if isinstance(candle, dict) else getattr(candle, "time", getattr(candle, "timestamp", None))
            if timestamp is None:
                return None
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            return {**values, "timestamp": timestamp}
        except (AttributeError, KeyError, TypeError, ValueError):
            return None
