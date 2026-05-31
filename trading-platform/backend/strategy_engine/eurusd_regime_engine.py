from datetime import datetime, timezone
from typing import Any

from backend.strategy_engine.strategy_models import EURUSDRegimeContext


class EURUSDRegimeEngine:
    """Classify EURUSD market regime using FX-scaled volatility and trend rules."""

    def detect(
        self,
        candles: list[Any] | None = None,
        indicator_context: Any | None = None,
        session_context: Any | None = None,
    ) -> EURUSDRegimeContext:
        if not candles:
            return EURUSDRegimeContext(
                symbol="EURUSD",
                regime="UNCLEAR",
                tradeability="AVOID",
                risk_mode="NO_TRADE",
                confidence=0.0,
                warnings=["No candle data supplied; EURUSD market regime context is a safe placeholder."],
            )

        try:
            normalized = [self._normalize(candle) for candle in candles]
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            return EURUSDRegimeContext(
                symbol="EURUSD",
                regime="UNCLEAR",
                tradeability="AVOID",
                risk_mode="NO_TRADE",
                confidence=0.0,
                warnings=[f"Invalid candle data supplied for EURUSD regime detection: {exc}"],
            )

        if len(normalized) < 8:
            return EURUSDRegimeContext(
                symbol="EURUSD",
                regime="UNCLEAR",
                tradeability="AVOID",
                risk_mode="NO_TRADE",
                confidence=0.0,
                warnings=["Insufficient EURUSD candle history for reliable regime detection."],
            )

        closes = [candle["close"] for candle in normalized]
        highs = [candle["high"] for candle in normalized]
        lows = [candle["low"] for candle in normalized]
        ranges = [max(candle["high"] - candle["low"], 0.0) for candle in normalized]
        atr = self._indicator_value(indicator_context, "atr") or self._atr(highs, lows, closes)
        last_close = closes[-1]
        volatility_ratio = atr / abs(last_close) if atr and last_close else 0.0
        volatility_score = round(volatility_ratio * 10000, 2)
        atr_state = self._atr_state(volatility_ratio)
        ema_alignment = self._ema_alignment(closes, indicator_context)
        trend_strength = self._trend_strength(closes, ranges)
        range_score = self._range_score(closes, highs, lows, ranges)
        abnormal_displacement = self._abnormal_displacement(ranges)
        session_alignment = self._session_aligned(session_context)

        warnings: list[str] = []
        regime = "UNCLEAR"
        if atr_state == "EXTREME" or abnormal_displacement:
            regime = "HIGH_VOLATILITY"
            warnings.append("EURUSD high volatility regime detected; use volatility protection and wait for stabilization.")
        elif atr_state == "LOW":
            regime = "LOW_VOLATILITY"
            warnings.append("EURUSD low volatility regime detected; movement quality is weak.")
        elif range_score >= 65 and trend_strength < 55:
            regime = "RANGING"
            warnings.append("EURUSD ranging regime detected; require stronger confirmation.")
        elif ema_alignment != "NEUTRAL" and trend_strength >= 55 and atr_state in {"NORMAL", "HIGH"}:
            regime = "TRENDING"
        elif ema_alignment == "NEUTRAL" and range_score >= 50:
            regime = "RANGING"
        else:
            warnings.append("EURUSD trend, volatility, and range signals conflict; regime is unclear.")

        context = EURUSDRegimeContext(
            symbol="EURUSD",
            regime=regime,
            trend_strength=trend_strength,
            volatility_score=volatility_score,
            range_score=range_score,
            atr_state=atr_state,
            ema_alignment=ema_alignment,
            session_alignment=session_alignment,
            warnings=warnings,
        )
        return self._score(context)

    def _score(self, context: EURUSDRegimeContext) -> EURUSDRegimeContext:
        score = 0.0
        if context.regime == "TRENDING" and context.trend_strength >= 55:
            score += 30.0
        if context.atr_state in {"NORMAL", "HIGH"} and context.regime != "HIGH_VOLATILITY":
            score += 20.0
        if context.session_alignment:
            score += 15.0
        if context.ema_alignment != "NEUTRAL":
            score += 15.0
        if context.regime in {"TRENDING", "RANGING"}:
            score += 10.0
        if context.regime != "HIGH_VOLATILITY" and context.atr_state != "EXTREME":
            score += 10.0

        if context.regime == "RANGING":
            score = min(score, 65.0)
        if context.regime == "LOW_VOLATILITY":
            score = min(score, 35.0)
        if context.regime == "HIGH_VOLATILITY":
            score = min(score, 40.0)
        if context.regime in {"UNCLEAR", "NEWS_VOLATILITY_PLACEHOLDER"}:
            score = min(score, 20.0)

        context.confidence = round(min(score, 100.0), 2)
        context.tradeability = self._tradeability(context.confidence)
        context.risk_mode = self._risk_mode(context.tradeability)
        return context

    def _trend_strength(self, closes: list[float], ranges: list[float]) -> float:
        if len(closes) < 2:
            return 0.0
        net_move = abs(closes[-1] - closes[0])
        path = sum(abs(closes[index] - closes[index - 1]) for index in range(1, len(closes)))
        range_baseline = sum(ranges) / len(ranges) if ranges else 0.0
        directional_efficiency = (net_move / path) * 70 if path > 0 else 0.0
        expansion = min((net_move / (range_baseline * len(closes))) * 30, 30.0) if range_baseline > 0 else 0.0
        return round(min(directional_efficiency + expansion, 100.0), 2)

    def _range_score(self, closes: list[float], highs: list[float], lows: list[float], ranges: list[float]) -> float:
        total_range = max(highs) - min(lows)
        average_range = sum(ranges) / len(ranges) if ranges else 0.0
        net_move = abs(closes[-1] - closes[0])
        if total_range <= 0 or average_range <= 0:
            return 0.0
        containment = min((average_range * len(closes) / total_range) * 40, 40.0)
        low_expansion = max(0.0, 35.0 - min((net_move / total_range) * 35, 35.0))
        repeated_turns = self._turn_score(closes)
        return round(min(containment + low_expansion + repeated_turns, 100.0), 2)

    def _turn_score(self, closes: list[float]) -> float:
        turns = 0
        for index in range(2, len(closes)):
            previous = closes[index - 1] - closes[index - 2]
            current = closes[index] - closes[index - 1]
            if previous and current and (previous > 0) != (current > 0):
                turns += 1
        return min(turns * 5.0, 25.0)

    def _abnormal_displacement(self, ranges: list[float]) -> bool:
        if len(ranges) < 8:
            return False
        baseline = sum(ranges[:-1]) / max(len(ranges) - 1, 1)
        return baseline > 0 and ranges[-1] >= baseline * 3.0 and ranges[-1] >= 0.0025

    def _ema_alignment(self, closes: list[float], indicator_context: Any | None) -> str:
        ema_50 = self._indicator_value(indicator_context, "ema_50")
        ema_200 = self._indicator_value(indicator_context, "ema_200")
        if ema_50 is None or ema_200 is None:
            ema_50 = self._ema(closes, min(8, len(closes)))
            ema_200 = self._ema(closes, min(21, len(closes)))
        if ema_50 is None or ema_200 is None:
            return "NEUTRAL"
        spread = abs(ema_50 - ema_200) / abs(closes[-1]) if closes[-1] else 0.0
        if spread < 0.00012:
            return "NEUTRAL"
        if ema_50 > ema_200:
            return "BULLISH"
        if ema_50 < ema_200:
            return "BEARISH"
        return "NEUTRAL"

    def _atr(self, highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> float:
        if len(closes) < 2:
            return 0.0
        start = max(1, len(closes) - period)
        true_ranges: list[float] = []
        for index in range(start, len(closes)):
            previous_close = closes[index - 1]
            true_ranges.append(
                max(
                    highs[index] - lows[index],
                    abs(highs[index] - previous_close),
                    abs(lows[index] - previous_close),
                )
            )
        return round(sum(true_ranges) / len(true_ranges), 5) if true_ranges else 0.0

    def _atr_state(self, volatility_ratio: float) -> str:
        if volatility_ratio < 0.00025:
            return "LOW"
        if volatility_ratio < 0.0018:
            return "NORMAL"
        if volatility_ratio < 0.0035:
            return "HIGH"
        return "EXTREME"

    def _ema(self, prices: list[float], period: int) -> float | None:
        if not prices or period <= 0 or len(prices) < period:
            return None
        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period
        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema
        return round(ema, 5)

    def _indicator_value(self, indicator_context: Any | None, field: str) -> float | None:
        if indicator_context is None:
            return None
        value = indicator_context.get(field) if isinstance(indicator_context, dict) else getattr(indicator_context, field, None)
        return float(value) if value is not None else None

    def _session_aligned(self, session_context: Any | None) -> bool:
        if session_context is None:
            return False
        if isinstance(session_context, dict):
            return session_context.get("session_quality") == "HIGH"
        return getattr(session_context, "session_quality", None) == "HIGH"

    def _tradeability(self, score: float) -> str:
        if score >= 75:
            return "HIGH"
        if score >= 50:
            return "MEDIUM"
        if score >= 25:
            return "LOW"
        return "AVOID"

    def _risk_mode(self, tradeability: str) -> str:
        if tradeability in {"HIGH", "MEDIUM"}:
            return "NORMAL"
        if tradeability == "LOW":
            return "REDUCED_RISK"
        return "NO_TRADE"

    def _normalize(self, candle: Any) -> dict[str, Any]:
        return {
            "time": self._time(candle),
            "open": float(self._value(candle, "open")),
            "high": float(self._value(candle, "high")),
            "low": float(self._value(candle, "low")),
            "close": float(self._value(candle, "close")),
        }

    def _time(self, candle: Any) -> datetime:
        raw = self._value(candle, "timestamp") if self._has_field(candle, "timestamp") else self._value(candle, "time")
        if isinstance(raw, datetime):
            return raw.replace(tzinfo=timezone.utc) if raw.tzinfo is None else raw.astimezone(timezone.utc)
        if isinstance(raw, (int, float)):
            return datetime.fromtimestamp(raw, tz=timezone.utc)
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).astimezone(timezone.utc)

    def _has_field(self, candle: Any, field: str) -> bool:
        return field in candle if isinstance(candle, dict) else hasattr(candle, field)

    def _value(self, candle: Any, field: str) -> Any:
        return candle[field] if isinstance(candle, dict) else getattr(candle, field)
