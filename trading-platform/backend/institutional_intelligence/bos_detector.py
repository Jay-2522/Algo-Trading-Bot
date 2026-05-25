from datetime import datetime, timezone
from math import isfinite
from typing import Any

from backend.institutional_intelligence.smc_models import SwingPoint
from backend.institutional_intelligence.structure_shift_models import StructureEvent


class BOSDetector:
    """Detect first directional price breaks through registered swing levels."""

    def detect_bos(
        self,
        candles: list[Any] | None,
        swings: list[SwingPoint] | None,
        symbol: str,
        timeframe: str,
    ) -> list[StructureEvent]:
        if not candles or not swings:
            return []
        events = []
        consumed_levels: set[tuple[str, float]] = set()
        ordered = sorted(swings, key=lambda swing: swing.index)
        for swing in ordered:
            direction = "BULLISH" if swing.type == "HIGH" else "BEARISH"
            key = (direction, swing.price)
            if key in consumed_levels:
                continue
            broken = self._first_break(candles, swing, direction)
            if broken is None:
                continue
            index, values, close_confirmed = broken
            events.append(
                StructureEvent(
                    symbol=symbol.strip().upper(),
                    timeframe=timeframe.strip().upper(),
                    event_type="BOS",
                    direction=direction,
                    break_level=swing.price,
                    break_price=round(values["close"] if close_confirmed else values["high" if direction == "BULLISH" else "low"], 5),
                    candle_index=index,
                    timestamp=values["timestamp"],
                    swing_reference=swing.model_dump(mode="json"),
                    close_confirmed=close_confirmed,
                    wick_break=not close_confirmed,
                    continuation=self._continuation(ordered, swing, direction),
                    reversal=False,
                    metadata={"break_class": "STRONG" if close_confirmed else "WEAK"},
                )
            )
            consumed_levels.add(key)
        return events

    def _first_break(
        self,
        candles: list[Any],
        swing: SwingPoint,
        direction: str,
    ) -> tuple[int, dict, bool] | None:
        for index in range(swing.index + 1, len(candles)):
            values = self._values(candles[index])
            if values is None:
                continue
            if direction == "BULLISH":
                close_break = values["close"] > swing.price
                wick_break = values["high"] > swing.price
            else:
                close_break = values["close"] < swing.price
                wick_break = values["low"] < swing.price
            if close_break or wick_break:
                return index, values, close_break
        return None

    def _continuation(self, swings: list[SwingPoint], swing: SwingPoint, direction: str) -> bool:
        same_type = [
            prior for prior in swings if prior.type == swing.type and prior.index < swing.index
        ]
        if not same_type:
            return True
        previous = same_type[-1]
        return swing.price > previous.price if direction == "BULLISH" else swing.price < previous.price

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
