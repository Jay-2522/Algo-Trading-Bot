from typing import Any

from backend.strategy_engine.strategy_models import IndicatorContext


class IndicatorContextBuilder:
    """Build safe indicator context from supplied candle data only."""

    def build_context(
        self,
        symbol: str = "XAUUSD",
        timeframe: str = "H1",
        candles: list[Any] | None = None,
    ) -> IndicatorContext:
        if not candles:
            return IndicatorContext(
                symbol=symbol,
                timeframe=timeframe,
                warnings=["No candle data supplied; indicator context is a safe placeholder."],
            )

        try:
            closes = [float(self._value(candle, "close")) for candle in candles]
            highs = [float(self._value(candle, "high")) for candle in candles]
            lows = [float(self._value(candle, "low")) for candle in candles]
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            return IndicatorContext(
                symbol=symbol,
                timeframe=timeframe,
                warnings=[f"Invalid candle data supplied; indicator context is a safe placeholder: {exc}"],
            )

        ema_50 = self._ema(closes, 50)
        ema_200 = self._ema(closes, 200)
        atr = self._atr(highs, lows, closes)
        rsi = self._rsi(closes)
        macd_bias = self._macd_bias(closes)
        trend_bias = "NEUTRAL"
        warnings: list[str] = []

        if ema_50 is None or ema_200 is None:
            warnings.append("Insufficient candles for EMA 50/200 trend confirmation.")
        elif ema_50 > ema_200:
            trend_bias = "BULLISH"
        elif ema_50 < ema_200:
            trend_bias = "BEARISH"

        if atr is None:
            warnings.append("Insufficient candles for ATR volatility context.")
        if rsi is None:
            warnings.append("Insufficient candles for RSI filter.")

        quality = "HIGH" if not warnings else "MEDIUM"
        if ema_50 is None and ema_200 is None and atr is None and rsi is None:
            quality = "LOW"

        return IndicatorContext(
            symbol=symbol,
            timeframe=timeframe,
            ema_50=ema_50,
            ema_200=ema_200,
            trend_bias=trend_bias,
            atr=atr,
            rsi=rsi,
            macd_bias=macd_bias,
            volatility_state=self._volatility_state(atr, closes[-1] if closes else None),
            indicator_quality=quality,
            warnings=warnings,
        )

    def _ema(self, prices: list[float], period: int) -> float | None:
        if len(prices) < period:
            return None
        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period
        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema
        return round(ema, 5)

    def _atr(self, highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> float | None:
        if len(closes) < period + 1:
            return None
        ranges: list[float] = []
        start = len(closes) - period
        for index in range(start, len(closes)):
            previous_close = closes[index - 1]
            true_range = max(
                highs[index] - lows[index],
                abs(highs[index] - previous_close),
                abs(lows[index] - previous_close),
            )
            ranges.append(true_range)
        return round(sum(ranges) / len(ranges), 5)

    def _rsi(self, closes: list[float], period: int = 14) -> float | None:
        if len(closes) < period + 1:
            return None
        gains: list[float] = []
        losses: list[float] = []
        for index in range(len(closes) - period, len(closes)):
            change = closes[index] - closes[index - 1]
            gains.append(max(change, 0.0))
            losses.append(abs(min(change, 0.0)))
        average_gain = sum(gains) / period
        average_loss = sum(losses) / period
        if average_loss == 0:
            return 100.0
        rs = average_gain / average_loss
        return round(100 - (100 / (1 + rs)), 2)

    def _macd_bias(self, closes: list[float]) -> str:
        ema_12 = self._ema(closes, 12)
        ema_26 = self._ema(closes, 26)
        if ema_12 is None or ema_26 is None:
            return "NEUTRAL"
        if ema_12 > ema_26:
            return "BULLISH"
        if ema_12 < ema_26:
            return "BEARISH"
        return "NEUTRAL"

    def _volatility_state(self, atr: float | None, last_close: float | None) -> str:
        if atr is None or not last_close:
            return "NORMAL"
        ratio = atr / abs(last_close)
        if ratio < 0.003:
            return "LOW"
        if ratio < 0.012:
            return "NORMAL"
        if ratio < 0.025:
            return "HIGH"
        return "EXTREME"

    def _value(self, candle: Any, field: str) -> Any:
        if isinstance(candle, dict):
            return candle[field]
        return getattr(candle, field)
