from typing import Any

from backend.ai_engine.ai_models import SignalScore


class SignalScorer:
    """Score setup quality from strategy, session, market-friction, and risk inputs."""

    def score_trade_setup(
        self,
        trend_analysis: dict[str, Any],
        liquidity_analysis: dict[str, Any],
        structure_analysis: dict[str, Any],
        session_info: dict[str, Any],
        spread_quality: float,
        risk_status: dict[str, Any],
        volatility_quality: float = 75,
    ) -> SignalScore:
        trend = trend_analysis.get("trend", "ranging")
        trend_score = 82 if trend in {"bullish", "bearish"} else 45

        zones = liquidity_analysis.get("potential_stop_hunt_zones", [])
        liquidity_score = 75 if zones else 55
        if session_info.get("high_liquidity"):
            liquidity_score = min(100, liquidity_score + 15)

        structure_detected = (
            structure_analysis.get("bos", {}).get("detected", False)
            or structure_analysis.get("choch", {}).get("detected", False)
        )
        structure_score = 80 if structure_detected else 45
        session_score = 90 if session_info.get("high_liquidity") else 40
        risk_score = 90 if risk_status.get("overall_status") == "OPERATIONAL" else 0

        factor_scores = {
            "trend_score": trend_score,
            "liquidity_score": liquidity_score,
            "structure_score": structure_score,
            "session_score": session_score,
            "volatility_score": volatility_quality,
            "spread_score": max(0, min(100, spread_quality)),
            "risk_score": risk_score,
        }
        overall_score = round(sum(factor_scores.values()) / len(factor_scores), 2)
        return SignalScore(**factor_scores, overall_score=overall_score)

