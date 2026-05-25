from typing import Any

from backend.institutional_intelligence.liquidity_sweep_detector import LiquiditySweepDetector
from backend.institutional_intelligence.liquidity_sweep_models import SweepContext
from backend.institutional_intelligence.smc_models import LiquidityPool


class SweepContextBuilder:
    """Summarize validated sweeps for downstream analysis-only confluence models."""

    HIGH_QUALITY_THRESHOLD = 70.0

    def __init__(self, detector: LiquiditySweepDetector | None = None) -> None:
        self.detector = detector or LiquiditySweepDetector()

    def build_sweep_context(
        self,
        symbol: str,
        timeframe: str,
        candles: list[Any] | None,
        liquidity_pools: list[LiquidityPool] | None,
    ) -> SweepContext:
        normalized_symbol = symbol.strip().upper()
        normalized_timeframe = timeframe.strip().upper()
        sweeps = self.detector.detect_sweeps(candles, liquidity_pools, normalized_symbol, normalized_timeframe)
        bullish = [sweep for sweep in sweeps if sweep.direction == "BULLISH"]
        bearish = [sweep for sweep in sweeps if sweep.direction == "BEARISH"]
        high_quality = [sweep for sweep in sweeps if sweep.strength >= self.HIGH_QUALITY_THRESHOLD]
        confidence = round(sum(sweep.strength for sweep in sweeps) / len(sweeps), 2) if sweeps else 0.0
        return SweepContext(
            symbol=normalized_symbol,
            timeframe=normalized_timeframe,
            sweeps=sweeps,
            latest_sweep=sweeps[-1] if sweeps else None,
            bullish_sweeps=bullish,
            bearish_sweeps=bearish,
            high_quality_sweeps=high_quality,
            confidence=confidence,
        )
