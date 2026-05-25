from typing import Any

from backend.institutional_intelligence.liquidity_sweep_models import SweepValidationResult
from backend.institutional_intelligence.smc_models import LiquidityPool
from backend.institutional_intelligence.sweep_validator import SweepValidator


class SweepStrengthScorer:
    """Score validated liquidity rejections using transparent capped factors."""

    def score_sweep(
        self,
        candle: Any,
        pool: LiquidityPool,
        validation_result: SweepValidationResult,
    ) -> float:
        if not validation_result.valid:
            return 0.0
        values = SweepValidator().values(candle)
        if values is None:
            return 0.0
        candle_range = max(values["high"] - values["low"], 1e-9)
        direction = SweepValidator().direction(candle, pool)
        sweep_distance = (
            values["high"] - pool.price_level
            if direction == "BEARISH"
            else pool.price_level - values["low"]
        )
        sweep_distance = max(sweep_distance, 0.0)
        distance_score = min(sweep_distance / candle_range * 100, 100.0)
        pool_score = min(pool.strength * 20.0, 100.0)
        close_score = 100.0 if validation_result.close_back_inside else 0.0
        score = (
            validation_result.rejection_strength * 0.35
            + close_score * 0.25
            + pool_score * 0.20
            + distance_score * 0.20
        )
        return round(min(max(score, 0.0), 100.0), 2)
