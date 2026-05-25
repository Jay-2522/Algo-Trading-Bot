from typing import Any

from backend.institutional_intelligence.fair_value_gap_models import FairValueGap, FVGMitigationResult


class FVGMitigationTracker:
    """Track price re-entry into previously identified imbalance zones."""

    def evaluate_mitigation(
        self,
        fvg: FairValueGap,
        candles_after_fvg: list[Any] | None,
    ) -> FVGMitigationResult:
        max_percent = 0.0
        touched = False
        for candle in candles_after_fvg or []:
            values = self._values(candle)
            if values is None:
                continue
            if fvg.direction == "BULLISH" and values["low"] <= fvg.gap_high:
                touched = True
                depth = fvg.gap_high - values["low"]
            elif fvg.direction == "BEARISH" and values["high"] >= fvg.gap_low:
                touched = True
                depth = values["high"] - fvg.gap_low
            else:
                continue
            percent = min(max(depth / fvg.gap_size * 100, 0.0), 100.0) if fvg.gap_size else 100.0
            max_percent = max(max_percent, percent)
        fully_mitigated = max_percent >= 100.0
        status = "MITIGATED" if fully_mitigated else "PARTIAL" if touched else "FRESH"
        reason = {
            "FRESH": "No future candle entered the imbalance zone.",
            "PARTIAL": "A future candle partially entered the imbalance zone.",
            "MITIGATED": "A future candle fully traded through the imbalance zone.",
        }[status]
        return FVGMitigationResult(
            status=status,
            mitigation_percent=round(max_percent, 2),
            touched=touched,
            fully_mitigated=fully_mitigated,
            reason=reason,
        )

    def update_fvg_mitigation(
        self,
        fvg: FairValueGap,
        candles_after_fvg: list[Any] | None,
    ) -> FairValueGap:
        result = self.evaluate_mitigation(fvg, candles_after_fvg)
        return fvg.model_copy(
            update={
                "mitigation_status": result.status,
                "mitigation_percent": result.mitigation_percent,
                "fresh": result.status == "FRESH",
                "metadata": {**fvg.metadata, "mitigation_reason": result.reason},
            }
        )

    def _values(self, candle: Any) -> dict | None:
        try:
            getter = candle.get if isinstance(candle, dict) else lambda field: getattr(candle, field)
            high = float(getter("high"))
            low = float(getter("low"))
            return {"high": high, "low": low} if high >= low else None
        except (AttributeError, KeyError, TypeError, ValueError):
            return None
