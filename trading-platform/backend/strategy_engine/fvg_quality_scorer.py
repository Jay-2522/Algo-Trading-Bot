from typing import Any

from backend.strategy_engine.strategy_models import FairValueGap


class FVGQualityScorer:
    """Score FVG quality for XAUUSD strategy confluence."""

    def score(
        self,
        fvg: FairValueGap,
        structure_context: Any | None = None,
        liquidity_context: Any | None = None,
        session_context: Any | None = None,
    ) -> tuple[float, str, str]:
        score = 0.0
        if fvg.displacement_strength > 0:
            score += 25.0
        if self._structure_aligned(fvg, structure_context):
            score += 25.0
        if self._liquidity_aligned(fvg, liquidity_context):
            score += 20.0
        if self._session_aligned(session_context):
            score += 15.0
        if fvg.size >= 1.0:
            score += 10.0
        if fvg.active and not fvg.mitigated:
            score += 5.0

        capped = round(min(score, 100.0), 2)
        if capped >= 75:
            quality = "HIGH"
        elif capped >= 50:
            quality = "MEDIUM"
        elif capped >= 25:
            quality = "LOW"
        else:
            quality = "NONE"

        reason = self._reason(fvg, structure_context, liquidity_context)
        return capped, quality, reason

    def _structure_aligned(self, fvg: FairValueGap, structure_context: Any | None) -> bool:
        if structure_context is None:
            return False
        bos = self._get(structure_context, "bos_direction", "NONE")
        choch = self._get(structure_context, "choch_direction", "NONE")
        if fvg.direction == "BULLISH":
            return bos == "BULLISH_BOS" or choch == "BULLISH_CHOCH"
        return bos == "BEARISH_BOS" or choch == "BEARISH_CHOCH"

    def _liquidity_aligned(self, fvg: FairValueGap, liquidity_context: Any | None) -> bool:
        if liquidity_context is None:
            return False
        sweep = self._get(liquidity_context, "sweep_direction", "NONE")
        if fvg.direction == "BULLISH":
            return sweep == "SELL_SIDE_SWEEP"
        return sweep == "BUY_SIDE_SWEEP"

    def _session_aligned(self, session_context: Any | None) -> bool:
        if session_context is None:
            return False
        return self._get(session_context, "session_quality", None) == "HIGH"

    def _reason(self, fvg: FairValueGap, structure_context: Any | None, liquidity_context: Any | None) -> str:
        structure = "aligned with structure" if self._structure_aligned(fvg, structure_context) else "not structure-aligned"
        liquidity = "aligned with liquidity sweep" if self._liquidity_aligned(fvg, liquidity_context) else "not liquidity-aligned"
        state = "active" if fvg.active else "mitigated"
        return f"{fvg.direction} FVG is {state}, {structure}, and {liquidity}."

    def _get(self, obj: Any, key: str, default: Any) -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)
