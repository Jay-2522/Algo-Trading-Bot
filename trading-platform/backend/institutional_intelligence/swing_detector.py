from datetime import datetime, timezone
from typing import Any

from backend.institutional_intelligence.smc_models import SwingPoint


class SwingDetector:
    """Identify local structural extremes from validated neighboring candles."""

    def detect_swings(self, candles: list[Any] | None, lookback: int = 2) -> list[SwingPoint]:
        if not candles or lookback < 1 or len(candles) < (lookback * 2) + 1:
            return []
        swings: list[SwingPoint] = []
        for index in range(lookback, len(candles) - lookback):
            window = candles[index - lookback : index + lookback + 1]
            parsed = [self._values(candle) for candle in window]
            if any(value is None for value in parsed):
                continue
            values = [value for value in parsed if value is not None]
            candidate = values[lookback]
            neighbors = values[:lookback] + values[lookback + 1 :]
            if candidate["high"] > max(value["high"] for value in neighbors):
                strength = candidate["high"] - max(value["high"] for value in neighbors)
                swings.append(
                    SwingPoint(
                        index=index,
                        timestamp=candidate["timestamp"],
                        price=round(candidate["high"], 5),
                        type="HIGH",
                        strength=round(strength, 5),
                    )
                )
            if candidate["low"] < min(value["low"] for value in neighbors):
                strength = min(value["low"] for value in neighbors) - candidate["low"]
                swings.append(
                    SwingPoint(
                        index=index,
                        timestamp=candidate["timestamp"],
                        price=round(candidate["low"], 5),
                        type="LOW",
                        strength=round(strength, 5),
                    )
                )
        return swings

    def get_latest_swing_high(self, candles: list[Any] | None) -> SwingPoint | None:
        highs = [swing for swing in self.detect_swings(candles) if swing.type == "HIGH"]
        return highs[-1] if highs else None

    def get_latest_swing_low(self, candles: list[Any] | None) -> SwingPoint | None:
        lows = [swing for swing in self.detect_swings(candles) if swing.type == "LOW"]
        return lows[-1] if lows else None

    def _values(self, candle: Any) -> dict | None:
        try:
            high = float(self._get(candle, "high"))
            low = float(self._get(candle, "low"))
            timestamp = self._get(candle, "time", self._get(candle, "timestamp", None))
            if high < low or timestamp is None:
                return None
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            return {"high": high, "low": low, "timestamp": timestamp}
        except (AttributeError, KeyError, TypeError, ValueError):
            return None

    def _get(self, candle: Any, field: str, default: Any = ...):
        if isinstance(candle, dict):
            if default is ...:
                return candle[field]
            return candle.get(field, default)
        if default is ...:
            return getattr(candle, field)
        return getattr(candle, field, default)
