from typing import Any

from backend.institutional_intelligence.position_management_models import EmergencyExitSignal, ManagedPosition


class EmergencyRiskExit:
    """Fail closed when simulated position state cannot be managed reliably."""

    def evaluate_emergency(
        self,
        position: ManagedPosition | None,
        risk_context: Any = None,
        structure_context: Any = None,
        candles: list[Any] | None = None,
        simulation_integrity: bool = True,
    ) -> EmergencyExitSignal:
        reasons: list[str] = []
        sources: list[str] = []
        status = self._get(risk_context, "overall_status")
        if status in {"BLOCKED", "FAILED", "ERROR", "UNAVAILABLE"}:
            sources.append("RISK_ENGINE")
            reasons.append(f"Risk engine status is {status}.")
        if not simulation_integrity:
            sources.append("SIMULATION_INTEGRITY")
            reasons.append("Simulation integrity validation failed.")
        if position is not None and not self._valid_geometry(position):
            sources.append("RR_GEOMETRY")
            reasons.append("Position contains impossible reward-to-risk geometry.")
        if self._conflicting_state(position, structure_context):
            sources.append("STRUCTURE_CONFLICT")
            reasons.append("Directional structure state conflicts with managed position.")
        if self._abnormal_volatility(candles):
            sources.append("VOLATILITY")
            reasons.append("Observed candle range represents an abnormal volatility spike.")
        triggered = bool(reasons)
        return EmergencyExitSignal(
            position_id=position.position_id if position else None,
            triggered=triggered,
            trigger_source=", ".join(sources) if sources else "NONE",
            severity="CRITICAL" if triggered else "INFO",
            shutdown_reason=" ".join(reasons) if reasons else "No emergency simulation shutdown condition detected.",
            emergency_action="CLOSE_SIMULATION_POSITION" if triggered and position else (
                "BLOCK_NEW_SIMULATIONS" if triggered else "NONE"
            ),
        )

    def _valid_geometry(self, position: ManagedPosition) -> bool:
        if position.initial_risk <= 0:
            return False
        if position.direction == "BUY":
            return position.initial_stop < position.entry_price < position.target_level
        return position.target_level < position.entry_price < position.initial_stop

    def _conflicting_state(self, position: ManagedPosition | None, context: Any) -> bool:
        if position is None or context is None:
            return False
        state = self._get(context, "current_structure_state")
        return (position.direction == "BUY" and state == "BEARISH") or (
            position.direction == "SELL" and state == "BULLISH"
        )

    def _abnormal_volatility(self, candles: list[Any] | None) -> bool:
        ranges: list[float] = []
        for candle in candles or []:
            try:
                high = float(self._get(candle, "high"))
                low = float(self._get(candle, "low"))
            except (TypeError, ValueError):
                continue
            ranges.append(max(0.0, high - low))
        if len(ranges) < 4:
            return False
        average = sum(ranges[:-1]) / len(ranges[:-1])
        return average > 0 and ranges[-1] > average * 4.0

    def _get(self, value: Any, key: str) -> Any:
        if value is None:
            return None
        return value.get(key) if isinstance(value, dict) else getattr(value, key, None)
