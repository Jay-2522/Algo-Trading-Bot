from datetime import datetime, timezone
from typing import Any

from backend.institutional_intelligence.liquidity_sweep_models import LiquiditySweep
from backend.institutional_intelligence.smc_models import LiquidityPool
from backend.institutional_intelligence.sweep_strength_scorer import SweepStrengthScorer
from backend.institutional_intelligence.sweep_validator import SweepValidator


class LiquiditySweepDetector:
    """Detect validated stop-liquidity rejections after liquidity pools form."""

    SWEEP_TYPES = {
        "EQUAL_HIGHS": "EQUAL_HIGH_SWEEP",
        "EQUAL_LOWS": "EQUAL_LOW_SWEEP",
        "PREVIOUS_HIGH": "PREVIOUS_HIGH_SWEEP",
        "PREVIOUS_LOW": "PREVIOUS_LOW_SWEEP",
        "EXTERNAL_LIQUIDITY": "EXTERNAL_LIQUIDITY_SWEEP",
        "INTERNAL_LIQUIDITY": "INTERNAL_LIQUIDITY_SWEEP",
    }

    def __init__(
        self,
        validator: SweepValidator | None = None,
        scorer: SweepStrengthScorer | None = None,
    ) -> None:
        self.validator = validator or SweepValidator()
        self.scorer = scorer or SweepStrengthScorer()

    def detect_sweeps(
        self,
        candles: list[Any] | None,
        liquidity_pools: list[LiquidityPool] | None,
        symbol: str,
        timeframe: str,
    ) -> list[LiquiditySweep]:
        if not candles or not liquidity_pools:
            return []
        sweeps = []
        for pool in liquidity_pools:
            formed_after = max(pool.related_swings, default=-1)
            for candle_index, candle in enumerate(candles):
                if candle_index <= formed_after:
                    continue
                sweep = self.detect_sweep_against_pool(candle, pool, candle_index, symbol, timeframe)
                if sweep is not None and sweep.valid:
                    sweeps.append(sweep)
                    break
        return sorted(sweeps, key=lambda sweep: (sweep.candle_index, sweep.strength))

    def detect_sweep_against_pool(
        self,
        candle: Any,
        pool: LiquidityPool,
        candle_index: int,
        symbol: str,
        timeframe: str,
    ) -> LiquiditySweep | None:
        validation = self.validator.validate_sweep(candle, pool)
        direction = self.validator.direction(candle, pool)
        values = self.validator.values(candle)
        timestamp = self._timestamp(candle)
        if not validation.valid or direction is None or values is None or timestamp is None:
            return None
        sweep_price = values["high"] if direction == "BEARISH" else values["low"]
        strength = self.scorer.score_sweep(candle, pool, validation)
        return LiquiditySweep(
            symbol=symbol.strip().upper(),
            timeframe=timeframe.strip().upper(),
            sweep_type=self.SWEEP_TYPES[pool.liquidity_type],
            direction=direction,
            swept_level=round(pool.price_level, 5),
            sweep_price=round(sweep_price, 5),
            candle_index=candle_index,
            timestamp=timestamp,
            close_back_inside=validation.close_back_inside,
            wick_rejection=validation.wick_rejection,
            strength=strength,
            valid=validation.valid,
            related_liquidity_pool=pool.pool_id,
            metadata={
                "liquidity_type": pool.liquidity_type,
                "pool_strength": pool.strength,
                "rejection_strength": validation.rejection_strength,
                "validation_reason": validation.reason,
            },
        )

    def _timestamp(self, candle: Any) -> datetime | None:
        try:
            if isinstance(candle, dict):
                timestamp = candle.get("time", candle.get("timestamp"))
            else:
                timestamp = getattr(candle, "time", getattr(candle, "timestamp", None))
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if timestamp is None:
                return None
            return timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)
        except (AttributeError, TypeError, ValueError):
            return None
