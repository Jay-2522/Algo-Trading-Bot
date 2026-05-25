from datetime import datetime, timezone
from typing import Any

from backend.institutional_intelligence.fair_value_gap_models import FairValueGap


class FairValueGapDetector:
    """Detect three-candle imbalances without generating execution signals."""

    def detect_fvgs(
        self,
        candles: list[Any] | None,
        symbol: str,
        timeframe: str,
    ) -> list[FairValueGap]:
        if not candles or len(candles) < 3:
            return []
        fvgs = []
        for index in range(1, len(candles) - 1):
            bullish = self.detect_bullish_fvg(candles, index, symbol, timeframe)
            bearish = self.detect_bearish_fvg(candles, index, symbol, timeframe)
            if bullish is not None:
                fvgs.append(bullish)
            if bearish is not None:
                fvgs.append(bearish)
        return fvgs

    def detect_bullish_fvg(
        self,
        candles: list[Any] | None,
        index: int,
        symbol: str,
        timeframe: str,
    ) -> FairValueGap | None:
        values = self._pattern(candles, index)
        if values is None or values[0]["high"] >= values[2]["low"]:
            return None
        return self._gap(
            symbol,
            timeframe,
            index,
            values[1]["timestamp"],
            "BULLISH",
            values[2]["low"],
            values[0]["high"],
        )

    def detect_bearish_fvg(
        self,
        candles: list[Any] | None,
        index: int,
        symbol: str,
        timeframe: str,
    ) -> FairValueGap | None:
        values = self._pattern(candles, index)
        if values is None or values[0]["low"] <= values[2]["high"]:
            return None
        return self._gap(
            symbol,
            timeframe,
            index,
            values[1]["timestamp"],
            "BEARISH",
            values[0]["low"],
            values[2]["high"],
        )

    def _gap(
        self,
        symbol: str,
        timeframe: str,
        middle_index: int,
        timestamp: datetime,
        direction: str,
        gap_high: float,
        gap_low: float,
    ) -> FairValueGap:
        return FairValueGap(
            symbol=symbol.strip().upper(),
            timeframe=timeframe.strip().upper(),
            direction=direction,
            start_index=middle_index - 1,
            middle_index=middle_index,
            end_index=middle_index + 1,
            timestamp=timestamp,
            gap_high=round(gap_high, 5),
            gap_low=round(gap_low, 5),
            gap_size=round(gap_high - gap_low, 5),
        )

    def _pattern(self, candles: list[Any] | None, index: int) -> list[dict] | None:
        if not candles or index < 1 or index >= len(candles) - 1:
            return None
        values = [self._values(candles[position]) for position in range(index - 1, index + 2)]
        return None if any(value is None for value in values) else [value for value in values if value is not None]

    def _values(self, candle: Any) -> dict | None:
        try:
            getter = candle.get if isinstance(candle, dict) else lambda field: getattr(candle, field)
            high = float(getter("high"))
            low = float(getter("low"))
            if isinstance(candle, dict):
                timestamp = candle.get("time", candle.get("timestamp"))
            else:
                timestamp = getattr(candle, "time", getattr(candle, "timestamp", None))
            if timestamp is None:
                return None
            if high < low:
                return None
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            return {"high": high, "low": low, "timestamp": timestamp}
        except (AttributeError, KeyError, TypeError, ValueError):
            return None
