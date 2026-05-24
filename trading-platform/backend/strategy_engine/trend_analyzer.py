from typing import Any, Dict, List


class TrendAnalyzer:
    """Lightweight trend analyzer using EMA 50 and EMA 200."""

    def calculate_ema(self, prices: list[float], period: int) -> float | None:
        """Calculate the latest EMA value for a price series."""

        if period <= 0:
            raise ValueError("EMA period must be greater than zero.")
        if len(prices) < period:
            return None

        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period
        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema
        return ema

    def determine_trend(self, candles: list[Any]) -> Dict[str, Any]:
        """Return a structured trend assessment without creating trade signals."""

        closes = [float(self._get_value(candle, "close")) for candle in candles]
        ema_50 = self.calculate_ema(closes, 50)
        ema_200 = self.calculate_ema(closes, 200)

        if ema_50 is None or ema_200 is None:
            trend = "ranging"
            confidence = 0.0
        elif ema_50 > ema_200:
            trend = "bullish"
            confidence = self._confidence(ema_50, ema_200)
        elif ema_50 < ema_200:
            trend = "bearish"
            confidence = self._confidence(ema_50, ema_200)
        else:
            trend = "ranging"
            confidence = 0.0

        return {
            "trend": trend,
            "ema_50": ema_50,
            "ema_200": ema_200,
            "confidence": confidence,
            "metadata": {
                "method": "ema_cross",
                "periods": [50, 200],
                "candles_analyzed": len(candles),
            },
        }

    def _confidence(self, ema_50: float, ema_200: float) -> float:
        if ema_200 == 0:
            return 0.0
        distance = abs(ema_50 - ema_200) / abs(ema_200)
        return round(min(distance * 100, 1.0), 4)

    def _get_value(self, candle: Any, field: str) -> Any:
        if isinstance(candle, dict):
            return candle[field]
        return getattr(candle, field)

