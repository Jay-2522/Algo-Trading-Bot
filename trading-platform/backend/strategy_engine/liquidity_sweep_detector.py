from datetime import datetime, timezone
from typing import Any

from backend.strategy_engine.strategy_models import LiquiditySweepContext


class LiquiditySweepDetector:
    """Detect foundational XAUUSD sweep context from supplied candles."""

    def detect(self, symbol: str = "XAUUSD", candles: list[Any] | None = None) -> LiquiditySweepContext:
        if not candles:
            return LiquiditySweepContext(
                symbol=symbol,
                warnings=["No candle data supplied; liquidity sweep context is a safe placeholder."],
            )

        try:
            latest = candles[-1]
            latest_high = float(self._value(latest, "high"))
            latest_low = float(self._value(latest, "low"))
            latest_time = self._time(latest)
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            return LiquiditySweepContext(
                symbol=symbol,
                warnings=[f"Invalid candle data supplied; liquidity context is a safe placeholder: {exc}"],
            )

        asian_candles = [candle for candle in candles if self._same_day_session(candle, latest_time, 0, 7)]
        previous_day_candles = [
            candle for candle in candles if self._time(candle).date() < latest_time.date()
        ]

        asian_high = self._max_value(asian_candles, "high")
        asian_low = self._min_value(asian_candles, "low")
        previous_day_high = self._max_value(previous_day_candles, "high")
        previous_day_low = self._min_value(previous_day_candles, "low")

        swept_asian_high = asian_high is not None and latest_high > asian_high
        swept_asian_low = asian_low is not None and latest_low < asian_low
        swept_previous_high = previous_day_high is not None and latest_high > previous_day_high
        swept_previous_low = previous_day_low is not None and latest_low < previous_day_low

        buy_side = swept_asian_high or swept_previous_high
        sell_side = swept_asian_low or swept_previous_low
        if buy_side and not sell_side:
            direction = "BUY_SIDE_SWEEP"
        elif sell_side and not buy_side:
            direction = "SELL_SIDE_SWEEP"
        else:
            direction = "NONE"

        warnings: list[str] = []
        if asian_high is None or asian_low is None:
            warnings.append("Asian high/low unavailable from supplied candles.")
        if previous_day_high is None or previous_day_low is None:
            warnings.append("Previous day high/low unavailable from supplied candles.")

        confidence = 0.0
        if direction != "NONE":
            confidence = 0.65 if not warnings else 0.45

        return LiquiditySweepContext(
            symbol=symbol,
            asian_high=asian_high,
            asian_low=asian_low,
            previous_day_high=previous_day_high,
            previous_day_low=previous_day_low,
            swept_asian_high=swept_asian_high,
            swept_asian_low=swept_asian_low,
            swept_previous_high=swept_previous_high,
            swept_previous_low=swept_previous_low,
            sweep_direction=direction,
            confidence=confidence,
            warnings=warnings,
        )

    def _same_day_session(self, candle: Any, reference: datetime, start_hour: int, end_hour: int) -> bool:
        candle_time = self._time(candle)
        return candle_time.date() == reference.date() and start_hour <= candle_time.hour < end_hour

    def _max_value(self, candles: list[Any], field: str) -> float | None:
        if not candles:
            return None
        return round(max(float(self._value(candle, field)) for candle in candles), 5)

    def _min_value(self, candles: list[Any], field: str) -> float | None:
        if not candles:
            return None
        return round(min(float(self._value(candle, field)) for candle in candles), 5)

    def _time(self, candle: Any) -> datetime:
        raw = self._value(candle, "timestamp") if self._has_field(candle, "timestamp") else self._value(candle, "time")
        if isinstance(raw, datetime):
            return raw.astimezone(timezone.utc)
        if isinstance(raw, (int, float)):
            return datetime.fromtimestamp(raw, tz=timezone.utc)
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).astimezone(timezone.utc)

    def _has_field(self, candle: Any, field: str) -> bool:
        if isinstance(candle, dict):
            return field in candle
        return hasattr(candle, field)

    def _value(self, candle: Any, field: str) -> Any:
        if isinstance(candle, dict):
            return candle[field]
        return getattr(candle, field)
