from datetime import datetime, timezone
from math import isfinite
from typing import Any

from backend.institutional_intelligence.order_block_models import OrderBlock


class OrderBlockDetector:
    """Detect opposing candles that immediately precede expanded impulse moves."""

    LOOKAHEAD_CANDLES = 3
    RECENT_RANGE_CANDLES = 5
    MIN_RANGE_EXPANSION = 1.5
    MIN_BODY_TO_RANGE = 0.6

    def detect_order_blocks(
        self,
        candles: list[Any] | None,
        symbol: str,
        timeframe: str,
    ) -> list[OrderBlock]:
        if not candles or len(candles) < 4:
            return []
        order_blocks = []
        for index in range(2, len(candles) - 1):
            bullish = self.detect_bullish_order_block(candles, index, symbol, timeframe)
            bearish = self.detect_bearish_order_block(candles, index, symbol, timeframe)
            if bullish is not None:
                order_blocks.append(bullish)
            if bearish is not None:
                order_blocks.append(bearish)
        return order_blocks

    def detect_bullish_order_block(
        self,
        candles: list[Any] | None,
        index: int,
        symbol: str,
        timeframe: str,
    ) -> OrderBlock | None:
        return self._detect(candles, index, symbol, timeframe, "BULLISH")

    def detect_bearish_order_block(
        self,
        candles: list[Any] | None,
        index: int,
        symbol: str,
        timeframe: str,
    ) -> OrderBlock | None:
        return self._detect(candles, index, symbol, timeframe, "BEARISH")

    def _detect(
        self,
        candles: list[Any] | None,
        index: int,
        symbol: str,
        timeframe: str,
        direction: str,
    ) -> OrderBlock | None:
        if not candles or index < 2 or index >= len(candles) - 1:
            return None
        candidate = self._values(candles[index])
        if candidate is None:
            return None
        opposing_candle = (
            candidate["close"] < candidate["open"]
            if direction == "BULLISH"
            else candidate["close"] > candidate["open"]
        )
        if not opposing_candle:
            return None
        baseline = [
            self._values(candle)
            for candle in candles[max(0, index - self.RECENT_RANGE_CANDLES) : index]
        ]
        recent = [value for value in baseline if value is not None]
        if len(recent) < 2:
            return None
        average_range = sum(value["high"] - value["low"] for value in recent) / len(recent)
        if average_range <= 0:
            return None
        for impulse_index in range(index + 1, min(len(candles), index + self.LOOKAHEAD_CANDLES + 1)):
            impulse = self._values(candles[impulse_index])
            if impulse is None:
                continue
            impulse_range = impulse["high"] - impulse["low"]
            body = abs(impulse["close"] - impulse["open"])
            impulse_direction = (
                impulse["close"] > impulse["open"]
                if direction == "BULLISH"
                else impulse["close"] < impulse["open"]
            )
            if (
                impulse_direction
                and impulse_range >= average_range * self.MIN_RANGE_EXPANSION
                and body >= impulse_range * self.MIN_BODY_TO_RANGE
            ):
                intermediate = [
                    self._values(candle)
                    for candle in candles[index + 1 : impulse_index]
                ]
                if any(
                    value is not None and self._is_opposing(value, direction)
                    for value in intermediate
                ):
                    continue
                return OrderBlock(
                    symbol=symbol.strip().upper(),
                    timeframe=timeframe.strip().upper(),
                    direction=direction,
                    candle_index=index,
                    timestamp=candidate["timestamp"],
                    high=round(candidate["high"], 5),
                    low=round(candidate["low"], 5),
                    open=round(candidate["open"], 5),
                    close=round(candidate["close"], 5),
                    zone_high=round(candidate["high"], 5),
                    zone_low=round(candidate["low"], 5),
                    displacement_confirmed=True,
                    metadata={
                        "displacement_index": impulse_index,
                        "average_recent_range": round(average_range, 5),
                        "displacement_range_ratio": round(impulse_range / average_range, 4),
                        "displacement_body_ratio": round(body / impulse_range, 4),
                    },
                )
        return None

    def _is_opposing(self, candle: dict, direction: str) -> bool:
        return (
            candle["close"] < candle["open"]
            if direction == "BULLISH"
            else candle["close"] > candle["open"]
        )

    def _values(self, candle: Any) -> dict | None:
        try:
            getter = candle.get if isinstance(candle, dict) else lambda field: getattr(candle, field)
            values = {field: float(getter(field)) for field in ("open", "high", "low", "close")}
            if not all(isfinite(value) for value in values.values()):
                return None
            if (
                values["high"] < values["low"]
                or values["high"] < max(values["open"], values["close"])
                or values["low"] > min(values["open"], values["close"])
            ):
                return None
            if isinstance(candle, dict):
                timestamp = candle.get("time", candle.get("timestamp"))
            else:
                timestamp = getattr(candle, "time", getattr(candle, "timestamp", None))
            if timestamp is None:
                return None
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            return {**values, "timestamp": timestamp}
        except (AttributeError, KeyError, TypeError, ValueError):
            return None
