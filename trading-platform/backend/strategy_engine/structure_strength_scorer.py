from typing import Any

from backend.strategy_engine.strategy_models import SMCStructureContext


class StructureStrengthScorer:
    """Score BOS/CHOCH structure confirmation for strategy confluence."""

    def score(
        self,
        context: SMCStructureContext,
        liquidity_context: Any | None = None,
        session_context: Any | None = None,
    ) -> tuple[float, float, str]:
        score = 0.0
        if context.bos_direction != "NONE":
            score += 30.0
        if context.choch_direction != "NONE":
            score += 35.0
        if context.post_sweep_confirmation:
            score += 20.0
        if self._session_aligned(session_context):
            score += 10.0
        if self._strong_close(context):
            score += 10.0
        if len(context.swing_highs) >= 1 and len(context.swing_lows) >= 1:
            score += 10.0

        strength = round(min(score, 100.0), 2)
        if strength >= 75:
            quality = "HIGH"
        elif strength >= 50:
            quality = "MEDIUM"
        elif strength >= 25:
            quality = "LOW"
        else:
            quality = "NONE"
        return strength, strength, quality

    def _session_aligned(self, session_context: Any | None) -> bool:
        if session_context is None:
            return False
        if isinstance(session_context, dict):
            return session_context.get("session_quality") == "HIGH"
        return getattr(session_context, "session_quality", None) == "HIGH"

    def _strong_close(self, context: SMCStructureContext) -> bool:
        if context.break_level is None or context.break_price is None:
            return False
        return abs(context.break_price - context.break_level) > 0
