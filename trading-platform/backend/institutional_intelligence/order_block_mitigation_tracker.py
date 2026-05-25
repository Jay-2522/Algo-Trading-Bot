from math import isfinite
from typing import Any

from backend.institutional_intelligence.order_block_models import OrderBlock, OrderBlockMitigationResult


class OrderBlockMitigationTracker:
    """Measure later price penetration into an order block zone."""

    def evaluate_mitigation(
        self,
        order_block: OrderBlock,
        candles_after_ob: list[Any] | None,
    ) -> OrderBlockMitigationResult:
        zone_size = order_block.zone_high - order_block.zone_low
        if zone_size <= 0:
            return OrderBlockMitigationResult(
                status="MITIGATED",
                mitigation_percent=100.0,
                touched=True,
                fully_mitigated=True,
                reason="Invalid zero-width order block zone is not actionable.",
            )
        max_percent = 0.0
        touched = False
        for candle in candles_after_ob or []:
            values = self._values(candle)
            if values is None:
                continue
            if order_block.direction == "BULLISH" and values["low"] <= order_block.zone_high:
                touched = True
                depth = order_block.zone_high - values["low"]
            elif order_block.direction == "BEARISH" and values["high"] >= order_block.zone_low:
                touched = True
                depth = values["high"] - order_block.zone_low
            else:
                continue
            percent = min(max(depth / zone_size * 100.0, 0.0), 100.0)
            max_percent = max(max_percent, percent)
        fully_mitigated = max_percent >= 100.0
        status = "MITIGATED" if fully_mitigated else "PARTIAL" if touched else "FRESH"
        reason = {
            "FRESH": "No future candle entered the order block zone.",
            "PARTIAL": "Future price partially entered the order block zone.",
            "MITIGATED": "Future price traded through the full order block zone.",
        }[status]
        return OrderBlockMitigationResult(
            status=status,
            mitigation_percent=round(max_percent, 2),
            touched=touched,
            fully_mitigated=fully_mitigated,
            reason=reason,
        )

    def update_order_block_mitigation(
        self,
        order_block: OrderBlock,
        candles_after_ob: list[Any] | None,
    ) -> OrderBlock:
        result = self.evaluate_mitigation(order_block, candles_after_ob)
        return order_block.model_copy(
            update={
                "mitigation_status": result.status,
                "mitigation_percent": result.mitigation_percent,
                "fresh": result.status == "FRESH",
                "metadata": {**order_block.metadata, "mitigation_reason": result.reason},
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
