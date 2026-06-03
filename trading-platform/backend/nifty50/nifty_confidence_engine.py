from backend.nifty50.nifty_strategy_models import (
    NIFTYFVGContext,
    NIFTYLiquidityContext,
    NIFTYOrderBlockContext,
    NIFTYStructureContext,
)


class NIFTYConfidenceEngine:
    def score(
        self,
        liquidity: NIFTYLiquidityContext,
        structure: NIFTYStructureContext,
        fvg: NIFTYFVGContext,
        order_block: NIFTYOrderBlockContext,
        regime: str,
    ) -> float:
        score = 0
        if liquidity.sweep_detected:
            score += 20
        if structure.bos_detected:
            score += 25
        if structure.choch_detected:
            score += 15
        if fvg.active_fvg_detected:
            score += 15
        if order_block.active_order_block:
            score += 15
        if regime in {"TRENDING_BULLISH", "TRENDING_BEARISH"}:
            score += 10
        return float(min(score, 100))
