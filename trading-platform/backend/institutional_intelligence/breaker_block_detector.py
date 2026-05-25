from datetime import datetime, timezone
from math import isfinite
from typing import Any

from backend.institutional_intelligence.breaker_block_models import BreakerBlock
from backend.institutional_intelligence.order_block_models import OrderBlock


class BreakerBlockDetector:
    """Identify valid order blocks invalidated by opposite displacement closes."""

    RECENT_RANGE_CANDLES = 5
    MIN_RANGE_EXPANSION = 1.5
    MIN_BODY_TO_RANGE = 0.6

    def detect_breaker_blocks(
        self,
        candles: list[Any] | None,
        order_blocks: list[OrderBlock] | None,
        symbol: str,
        timeframe: str,
    ) -> list[BreakerBlock]:
        if not candles or not order_blocks:
            return []
        breakers = []
        consumed_sources: set[str] = set()
        for order_block in order_blocks:
            if not order_block.valid or order_block.ob_id in consumed_sources:
                continue
            breaker = self.detect_breaker_block(candles, order_block, symbol, timeframe)
            if breaker is not None:
                breakers.append(breaker)
                consumed_sources.add(order_block.ob_id)
        return sorted(breakers, key=lambda breaker: breaker.candle_index)

    def detect_breaker_block(
        self,
        candles: list[Any] | None,
        source_order_block: OrderBlock,
        symbol: str,
        timeframe: str,
    ) -> BreakerBlock | None:
        if not candles or not source_order_block.valid:
            return None
        direction = "BULLISH" if source_order_block.direction == "BEARISH" else "BEARISH"
        origin_displacement = int(
            source_order_block.metadata.get("displacement_index", source_order_block.candle_index)
        )
        for index in range(origin_displacement + 1, len(candles)):
            candle = self._values(candles[index])
            if candle is None or not self._closed_through(candle, source_order_block, direction):
                continue
            displacement = self._displacement_metrics(candles, index, direction)
            if displacement is None:
                continue
            return BreakerBlock(
                symbol=symbol.strip().upper(),
                timeframe=timeframe.strip().upper(),
                direction=direction,
                source_order_block_id=source_order_block.ob_id,
                candle_index=index,
                timestamp=candle["timestamp"],
                original_ob_direction=source_order_block.direction,
                break_price=round(candle["close"], 5),
                zone_high=source_order_block.zone_high,
                zone_low=source_order_block.zone_low,
                structure_shift_confirmed=True,
                metadata={
                    "source_ob_candle_index": source_order_block.candle_index,
                    "source_ob_valid": source_order_block.valid,
                    "source_ob_strength": source_order_block.strength,
                    "invalidation_index": index,
                    "displacement_index": index,
                    **displacement,
                },
            )
        return None

    def _closed_through(self, candle: dict, source: OrderBlock, direction: str) -> bool:
        if direction == "BULLISH":
            return candle["close"] > source.zone_high and candle["close"] > candle["open"]
        return candle["close"] < source.zone_low and candle["close"] < candle["open"]

    def _displacement_metrics(self, candles: list[Any], index: int, direction: str) -> dict | None:
        current = self._values(candles[index])
        prior = [
            self._values(candle)
            for candle in candles[max(0, index - self.RECENT_RANGE_CANDLES) : index]
        ]
        recent = [value for value in prior if value is not None]
        if current is None or len(recent) < 2:
            return None
        average_range = sum(value["high"] - value["low"] for value in recent) / len(recent)
        impulse_range = current["high"] - current["low"]
        body = abs(current["close"] - current["open"])
        aligned = current["close"] > current["open"] if direction == "BULLISH" else current["close"] < current["open"]
        if (
            not aligned
            or average_range <= 0
            or impulse_range < average_range * self.MIN_RANGE_EXPANSION
            or body < impulse_range * self.MIN_BODY_TO_RANGE
        ):
            return None
        return {
            "average_recent_range": round(average_range, 5),
            "displacement_range_ratio": round(impulse_range / average_range, 4),
            "displacement_body_ratio": round(body / impulse_range, 4),
        }

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
