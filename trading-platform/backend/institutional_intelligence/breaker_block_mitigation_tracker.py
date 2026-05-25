from math import isfinite
from typing import Any

from backend.institutional_intelligence.breaker_block_models import BreakerBlock, BreakerBlockMitigationResult


class BreakerBlockMitigationTracker:
    """Track retests of a converted breaker reaction zone after invalidation."""

    def evaluate_mitigation(
        self,
        breaker_block: BreakerBlock,
        candles_after_breaker: list[Any] | None,
    ) -> BreakerBlockMitigationResult:
        zone_size = breaker_block.zone_high - breaker_block.zone_low
        if zone_size <= 0:
            return BreakerBlockMitigationResult(
                status="MITIGATED",
                mitigation_percent=100.0,
                touched=True,
                fully_mitigated=True,
                reason="Invalid zero-width breaker zone is not analytically usable.",
            )
        touched = False
        max_percent = 0.0
        for candle in candles_after_breaker or []:
            values = self._values(candle)
            if values is None:
                continue
            if breaker_block.direction == "BULLISH" and values["low"] <= breaker_block.zone_high:
                touched = True
                depth = breaker_block.zone_high - values["low"]
            elif breaker_block.direction == "BEARISH" and values["high"] >= breaker_block.zone_low:
                touched = True
                depth = values["high"] - breaker_block.zone_low
            else:
                continue
            percent = min(max(depth / zone_size * 100.0, 0.0), 100.0)
            max_percent = max(max_percent, percent)
        fully_mitigated = max_percent >= 100.0
        status = "MITIGATED" if fully_mitigated else "PARTIALLY_MITIGATED" if touched else "FRESH"
        reason = {
            "FRESH": "No future candle revisited the breaker zone.",
            "PARTIALLY_MITIGATED": "Future price partially entered the breaker reaction zone.",
            "MITIGATED": "Future price traded through the full breaker reaction zone.",
        }[status]
        return BreakerBlockMitigationResult(
            status=status,
            mitigation_percent=round(max_percent, 2),
            touched=touched,
            fully_mitigated=fully_mitigated,
            reason=reason,
        )

    def update_breaker_mitigation(
        self,
        breaker_block: BreakerBlock,
        candles_after_breaker: list[Any] | None,
    ) -> BreakerBlock:
        result = self.evaluate_mitigation(breaker_block, candles_after_breaker)
        return breaker_block.model_copy(
            update={
                "mitigation_status": result.status,
                "mitigation_percent": result.mitigation_percent,
                "fresh": result.status == "FRESH",
                "metadata": {**breaker_block.metadata, "mitigation_reason": result.reason},
            }
        )

    def _values(self, candle: Any) -> dict | None:
        try:
            getter = candle.get if isinstance(candle, dict) else lambda field: getattr(candle, field)
            high = float(getter("high"))
            low = float(getter("low"))
            if not isfinite(high) or not isfinite(low) or high < low:
                return None
            return {"high": high, "low": low}
        except (AttributeError, KeyError, TypeError, ValueError):
            return None
