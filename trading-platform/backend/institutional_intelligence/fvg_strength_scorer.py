from typing import Any

from backend.institutional_intelligence.fair_value_gap_models import FairValueGap, FVGStrengthScore


class FVGStrengthScorer:
    """Score imbalances using size, impulse, lifecycle, and bias alignment."""

    def score_fvg(
        self,
        fvg: FairValueGap,
        candles: list[Any] | None,
        displacement_context: Any = None,
    ) -> FVGStrengthScore:
        values = [self._values(candle) for candle in (candles or [])]
        recent = [
            value
            for value in values[max(0, fvg.start_index - 5) : fvg.end_index + 1]
            if value is not None
        ]
        average_range = (
            sum(value["high"] - value["low"] for value in recent) / len(recent)
            if recent
            else 0.0
        )
        gap_ratio = fvg.gap_size / average_range if average_range else 0.0
        gap_size_score = min(gap_ratio * 25.0, 25.0)
        middle = values[fvg.middle_index] if fvg.middle_index < len(values) else None
        body_ratio = (
            abs(middle["close"] - middle["open"]) / (middle["high"] - middle["low"])
            if middle and middle["high"] > middle["low"]
            else 0.0
        )
        displacement_score = min(body_ratio * 25.0, 25.0)
        freshness_score = {"FRESH": 20.0, "PARTIAL": 10.0, "MITIGATED": 0.0}[fvg.mitigation_status]
        mitigation_score = max(20.0 * (1.0 - fvg.mitigation_percent / 100.0), 0.0)
        bias = self._bias(displacement_context)
        confluence_score = 10.0 if bias == fvg.direction else 3.0 if bias in {"RANGING", "UNCLEAR", None} else 0.0
        score = round(
            min(gap_size_score + displacement_score + freshness_score + mitigation_score + confluence_score, 100.0),
            2,
        )
        return FVGStrengthScore(
            score=score,
            gap_size_score=round(gap_size_score, 2),
            displacement_score=round(displacement_score, 2),
            freshness_score=freshness_score,
            mitigation_score=round(mitigation_score, 2),
            confluence_score=confluence_score,
            reason=f"FVG scored with {fvg.mitigation_status.lower()} lifecycle and {bias or 'no'} structural bias.",
        )

    def _bias(self, context: Any) -> str | None:
        if context is None:
            return None
        if isinstance(context, dict):
            return context.get("bias")
        return getattr(context, "bias", None)

    def _values(self, candle: Any) -> dict | None:
        try:
            getter = candle.get if isinstance(candle, dict) else lambda field: getattr(candle, field)
            values = {field: float(getter(field)) for field in ("open", "high", "low", "close")}
            return values if values["high"] >= values["low"] else None
        except (AttributeError, KeyError, TypeError, ValueError):
            return None
