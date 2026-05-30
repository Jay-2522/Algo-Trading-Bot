from typing import Any

from backend.strategy_engine.strategy_models import OrderBlock


class OrderBlockQualityScorer:
    """Score XAUUSD order block quality from structure, liquidity, FVG, and session confluence."""

    def score(
        self,
        order_block: OrderBlock,
        structure_context: Any | None = None,
        liquidity_context: Any | None = None,
        session_context: Any | None = None,
    ) -> tuple[float, str, str]:
        score = 0.0
        if self._bos_aligned(order_block, structure_context):
            score += 25.0
        if self._choch_aligned(order_block, structure_context):
            score += 25.0
        if order_block.aligned_with_fvg or self._fvg_aligned(order_block, structure_context):
            score += 20.0
        if order_block.aligned_with_liquidity or self._liquidity_aligned(order_block, liquidity_context):
            score += 15.0
        if self._session_aligned(session_context):
            score += 10.0
        if order_block.fresh:
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

        return capped, quality, self._reason(order_block, structure_context, liquidity_context)

    def _bos_aligned(self, order_block: OrderBlock, structure_context: Any | None) -> bool:
        bos = self._get(structure_context, "bos_direction", "NONE")
        if order_block.direction == "BULLISH":
            return bos == "BULLISH_BOS"
        return bos == "BEARISH_BOS"

    def _choch_aligned(self, order_block: OrderBlock, structure_context: Any | None) -> bool:
        choch = self._get(structure_context, "choch_direction", "NONE")
        if order_block.direction == "BULLISH":
            return choch == "BULLISH_CHOCH"
        return choch == "BEARISH_CHOCH"

    def _fvg_aligned(self, order_block: OrderBlock, structure_context: Any | None) -> bool:
        if structure_context is None:
            return False
        latest = self._get(structure_context, "latest_fvg", None)
        if latest is not None:
            return self._get(latest, "direction", "NONE") == order_block.direction
        gaps = self._get(structure_context, "fair_value_gaps", [])
        return any(
            self._get(gap, "direction", "NONE") == order_block.direction
            for gap in gaps
        )

    def _liquidity_aligned(self, order_block: OrderBlock, liquidity_context: Any | None) -> bool:
        sweep = self._get(liquidity_context, "sweep_direction", "NONE")
        if order_block.direction == "BULLISH":
            return sweep == "SELL_SIDE_SWEEP"
        return sweep == "BUY_SIDE_SWEEP"

    def _session_aligned(self, session_context: Any | None) -> bool:
        return self._get(session_context, "session_quality", None) == "HIGH"

    def _reason(self, order_block: OrderBlock, structure_context: Any | None, liquidity_context: Any | None) -> str:
        structure = "aligned with BOS/CHOCH" if (
            self._bos_aligned(order_block, structure_context) or self._choch_aligned(order_block, structure_context)
        ) else "not structure-aligned"
        liquidity = "aligned with liquidity sweep" if self._liquidity_aligned(order_block, liquidity_context) else "not liquidity-aligned"
        fvg = "aligned with FVG" if (order_block.aligned_with_fvg or self._fvg_aligned(order_block, structure_context)) else "not FVG-aligned"
        state = "fresh" if order_block.fresh else "mitigated" if order_block.mitigated else "active"
        if order_block.broken:
            state = "broken"
        return f"{order_block.direction} order block is {state}, {structure}, {liquidity}, and {fvg}."

    def _get(self, obj: Any | None, key: str, default: Any) -> Any:
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)
