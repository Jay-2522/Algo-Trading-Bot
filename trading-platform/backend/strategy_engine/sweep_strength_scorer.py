from typing import Any

from backend.strategy_engine.strategy_models import LiquiditySweepContext


class SweepStrengthScorer:
    """Score detected liquidity sweeps for strategy confluence."""

    def score(self, context: LiquiditySweepContext, session_context: Any | None = None) -> tuple[float, float, str]:
        if context.sweep_direction == "NONE":
            return 0.0, 0.0, "NONE"

        score = 0.0
        if context.swept_asian_high or context.swept_asian_low:
            score += 25.0
        if context.swept_previous_high or context.swept_previous_low:
            score += 30.0
        if context.active_sweep_level in {"EQUAL_HIGHS", "EQUAL_LOWS"}:
            score += 20.0
        if context.rejection_detected:
            score += 20.0
        if self._is_session_aligned(context, session_context):
            score += 15.0
        if context.volume_spike_detected:
            score += 10.0
        if context.sweep_price is not None and self._active_level_price(context) is not None:
            score += min(abs(context.sweep_price - self._active_level_price(context)) / 2.0, 5.0)

        sweep_strength = round(min(score, 100.0), 2)
        confidence = sweep_strength if context.rejection_detected else min(sweep_strength, 45.0)
        if confidence >= 75:
            quality = "HIGH"
        elif confidence >= 50:
            quality = "MEDIUM"
        elif confidence > 0:
            quality = "LOW"
        else:
            quality = "NONE"
        return sweep_strength, round(confidence, 2), quality

    def _is_session_aligned(self, context: LiquiditySweepContext, session_context: Any | None) -> bool:
        if session_context is not None and hasattr(session_context, "session_quality"):
            return session_context.session_quality == "HIGH"
        return context.session_alignment

    def _active_level_price(self, context: LiquiditySweepContext) -> float | None:
        mapping = {
            "ASIAN_HIGH": context.asian_high,
            "ASIAN_LOW": context.asian_low,
            "PREVIOUS_DAY_HIGH": context.previous_day_high,
            "PREVIOUS_DAY_LOW": context.previous_day_low,
        }
        if context.active_sweep_level in mapping:
            return mapping[context.active_sweep_level]
        for pool in context.liquidity_pools:
            if pool.get("type") == context.active_sweep_level:
                return float(pool["level"])
        return None
