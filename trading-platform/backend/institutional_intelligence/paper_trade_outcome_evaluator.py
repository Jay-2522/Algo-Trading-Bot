from typing import Any


class PaperTradeOutcomeEvaluator:
    """Calculate simulated lifecycle outcomes without execution side effects."""

    def calculate_pnl_points(self, position: Any, close_price: float) -> float:
        entry = float(self._get(position, "entry_price") or 0.0)
        direction = self._get(position, "direction")
        pnl = float(close_price) - entry if direction == "BUY" else entry - float(close_price)
        return round(pnl, 8)

    def calculate_rr_result(self, position: Any, close_price: float) -> float:
        entry = float(self._get(position, "entry_price") or 0.0)
        invalidation = self._get(position, "invalidation_level")
        if invalidation is None:
            return 0.0
        initial_risk = abs(entry - float(invalidation))
        if initial_risk <= 0.0:
            return 0.0
        return round(self.calculate_pnl_points(position, close_price) / initial_risk, 2)

    def classify_outcome(self, position: Any) -> str:
        reason = str(self._get(position, "close_reason") or "").upper()
        if reason in {"TARGET", "TAKE_PROFIT"}:
            return "WIN"
        if reason in {"INVALIDATION", "STOP", "STOP_LOSS"}:
            return "LOSS"
        if reason == "EXPIRED":
            return "EXPIRED"
        if reason == "CANCELLED":
            return "CANCELLED"
        pnl = float(self._get(position, "pnl_points") or 0.0)
        if self._get(position, "status") != "CLOSED":
            return "OPEN"
        if pnl > 0.0:
            return "WIN"
        if pnl < 0.0:
            return "LOSS"
        return "BREAKEVEN"

    def _get(self, value: Any, key: str) -> Any:
        if value is None:
            return None
        return value.get(key) if isinstance(value, dict) else getattr(value, key, None)
