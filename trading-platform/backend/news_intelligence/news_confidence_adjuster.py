from typing import Any


class NewsConfidenceAdjuster:
    """Apply the final unified news decision to a confidence score."""

    def apply(self, base_confidence: float, unified_decision: Any) -> float:
        action = self._get(unified_decision, "final_trade_action", "ALLOW")
        adjustment = float(self._get(unified_decision, "confidence_adjustment", 0.0) or 0.0)
        cap = self._get(unified_decision, "confidence_cap", None)

        if action == "BLOCK":
            return self._clamp(min(base_confidence, float(cap if cap is not None else 0.0)))
        if action == "WAIT_FOR_STABILIZATION":
            return self._clamp(min(base_confidence, float(cap if cap is not None else 30.0)))
        if action == "REDUCE_RISK":
            return self._clamp(base_confidence + adjustment)
        return self._clamp(base_confidence + adjustment)

    def _clamp(self, value: float) -> float:
        return round(max(0.0, min(100.0, float(value))), 2)

    def _get(self, obj: Any | None, key: str, default: Any) -> Any:
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)
