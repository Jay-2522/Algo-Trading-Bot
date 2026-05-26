from typing import Any

from backend.institutional_intelligence.session_models import KillzoneStatus, SessionLiquidityProfile, SessionManipulationSignal


class SessionQualityScorer:
    """Provide bounded time-of-day quality using observable session evidence."""

    def score_session_quality(
        self,
        killzone_status: KillzoneStatus,
        liquidity_profile: SessionLiquidityProfile,
        manipulation_signals: list[SessionManipulationSignal] | None = None,
        news_status: Any = None,
    ) -> float:
        score = 0.0
        if killzone_status.active_killzone:
            score += 25.0 if killzone_status.high_liquidity_window else 15.0
        if liquidity_profile.liquidity_quality == "HIGH":
            score += 25.0
        elif liquidity_profile.liquidity_quality == "NORMAL":
            score += 15.0
        elif liquidity_profile.liquidity_quality == "LOW":
            score += 5.0
        confirmed = [
            signal for signal in manipulation_signals or [] if signal.confirmation and signal.confidence >= 60.0
        ]
        if confirmed:
            score += 20.0
        if liquidity_profile.volatility_quality == "HIGH":
            score += 15.0
        elif liquidity_profile.volatility_quality == "NORMAL":
            score += 10.0
        elif liquidity_profile.volatility_quality == "LOW":
            score += 5.0
        if self._blocked_by_news(news_status):
            score -= 30.0
        elif news_status is not None:
            score += 15.0
        else:
            score += 7.5
        return round(min(max(score, 0.0), 100.0), 2)

    def _blocked_by_news(self, status: Any) -> bool:
        if status is None:
            return False
        active = status.get("active_blackout") if isinstance(status, dict) else getattr(status, "active_blackout", False)
        allowed = status.get("trading_allowed") if isinstance(status, dict) else getattr(status, "trading_allowed", True)
        return bool(active) or allowed is False
