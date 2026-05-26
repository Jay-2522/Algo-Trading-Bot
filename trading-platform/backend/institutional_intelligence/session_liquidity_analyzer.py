from typing import Any

from backend.institutional_intelligence.session_models import SessionLiquidityProfile, TradingSessionRange


class SessionLiquidityAnalyzer:
    """Grade participation quality using observed range behavior and validated sweeps."""

    def analyze_liquidity(
        self,
        candles: list[Any] | None,
        session_range: TradingSessionRange,
        sweep_context: Any = None,
    ) -> SessionLiquidityProfile:
        ranges = [
            high - low
            for candle in candles or []
            if (high := self._number(candle, "high")) is not None
            and (low := self._number(candle, "low")) is not None
            and high >= low
        ]
        average = sum(ranges) / len(ranges) if ranges else 0.0
        expansion = session_range.range_size / average if session_range.valid and average > 0 else 0.0
        sweeps = self._items(sweep_context, "sweeps")
        sweep_detected = any(self._get(sweep, "valid") is not False for sweep in sweeps)
        breakout = session_range.valid and expansion >= 2.0

        if not session_range.valid:
            volatility, liquidity, confidence = "POOR", "POOR", 0.0
        elif expansion >= 2.0:
            volatility = "HIGH"
            liquidity = "HIGH" if sweep_detected else "NORMAL"
            confidence = 85.0 if sweep_detected else 70.0
        elif expansion >= 1.0:
            volatility = "NORMAL"
            liquidity = "HIGH" if sweep_detected else "NORMAL"
            confidence = 75.0 if sweep_detected else 60.0
        elif expansion >= 0.5:
            volatility = "LOW"
            liquidity = "NORMAL" if sweep_detected else "LOW"
            confidence = 50.0 if sweep_detected else 35.0
        else:
            volatility = "POOR"
            liquidity = "LOW" if sweep_detected else "POOR"
            confidence = 25.0 if sweep_detected else 10.0
        return SessionLiquidityProfile(
            session_name=session_range.session_name,
            liquidity_quality=liquidity,
            volatility_quality=volatility,
            range_expansion=round(expansion, 2),
            sweep_detected=sweep_detected,
            breakout_detected=breakout,
            confidence=confidence,
        )

    def _number(self, candle: Any, key: str) -> float | None:
        value = candle.get(key) if isinstance(candle, dict) else getattr(candle, key, None)
        try:
            number = float(value)
            return number if number == number and abs(number) != float("inf") else None
        except (TypeError, ValueError):
            return None

    def _items(self, context: Any, key: str) -> list[Any]:
        if context is None:
            return []
        value = context.get(key, []) if isinstance(context, dict) else getattr(context, key, [])
        return list(value or [])

    def _get(self, value: Any, key: str) -> Any:
        if value is None:
            return None
        return value.get(key) if isinstance(value, dict) else getattr(value, key, None)
