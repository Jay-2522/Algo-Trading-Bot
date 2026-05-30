from typing import Any

from backend.strategy_engine.strategy_models import MarketRegimeContext


class RegimeQualityScorer:
    """Score market regime tradeability for XAUUSD strategy analysis."""

    def score(self, context: MarketRegimeContext, session_context: Any | None = None) -> MarketRegimeContext:
        score = 0.0
        if context.regime == "TRENDING" and context.trend_strength >= 55:
            score += 30.0
        if context.atr_state in {"NORMAL", "HIGH"} and context.regime != "HIGH_VOLATILITY":
            score += 20.0
        if self._session_aligned(session_context) or context.session_alignment:
            score += 15.0
        if context.ema_alignment != "NEUTRAL":
            score += 15.0
        if context.regime in {"TRENDING", "RANGING"} and context.regime != "UNCLEAR":
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

    def _session_aligned(self, session_context: Any | None) -> bool:
        if session_context is None:
            return False
        if isinstance(session_context, dict):
            return session_context.get("session_quality") == "HIGH"
        return getattr(session_context, "session_quality", None) == "HIGH"
