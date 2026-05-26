class SimulationRiskEstimator:
    """Estimate analytical reward-to-risk for a non-executing simulation intent."""

    def estimate_rr(
        self,
        entry_low: float | None,
        entry_high: float | None,
        invalidation_level: float | None,
        target_level: float | None,
        direction: str,
    ) -> float:
        if None in {entry_low, entry_high, invalidation_level, target_level} or direction not in {"BUY", "SELL"}:
            return 0.0
        low = float(entry_low)
        high = float(entry_high)
        if high <= low:
            return 0.0
        entry = (low + high) / 2.0
        if direction == "BUY":
            risk = entry - float(invalidation_level)
            reward = float(target_level) - entry
        else:
            risk = float(invalidation_level) - entry
            reward = entry - float(target_level)
        if risk <= 0.0 or reward <= 0.0:
            return 0.0
        return round(reward / risk, 2)

    def classify_risk_quality(self, rr: float, valid_geometry: bool = True) -> str:
        if not valid_geometry or rr <= 0.0:
            return "INVALID"
        if rr >= 3.0:
            return "EXCELLENT"
        if rr >= 2.0:
            return "GOOD"
        if rr >= 1.5:
            return "ACCEPTABLE"
        return "POOR"
