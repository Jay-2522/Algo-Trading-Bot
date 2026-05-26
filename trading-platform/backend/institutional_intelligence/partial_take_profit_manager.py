from typing import Any

from backend.institutional_intelligence.position_management_models import ManagedPosition, PartialTakeProfit


class PartialTakeProfitManager:
    """Apply deterministic simulated profit reductions while preserving a runner."""

    def __init__(self, close_runner_at_3r: bool = False) -> None:
        self.close_runner_at_3r = close_runner_at_3r

    def evaluate(self, position: ManagedPosition, candles: list[Any] | None) -> tuple[ManagedPosition, list[PartialTakeProfit]]:
        excursion = self._favorable_excursion_rr(position, candles)
        updated = position
        actions: list[PartialTakeProfit] = []
        if excursion >= 1.0 and not updated.tp1_achieved:
            updated, action = self._reduce(updated, "TP1", 1.0, 50.0)
            updated = updated.model_copy(update={"tp1_achieved": True})
            actions.append(action)
        if excursion >= 2.0 and not updated.tp2_achieved:
            updated, action = self._reduce(updated, "TP2", 2.0, 25.0)
            updated = updated.model_copy(update={"tp2_achieved": True})
            actions.append(action)
        if excursion >= 3.0 and self.close_runner_at_3r and updated.remaining_size > 0:
            reduction = round(updated.remaining_size / updated.original_size * 100.0, 2)
            updated, action = self._reduce(updated, "TP3", 3.0, reduction)
            actions.append(action.model_copy(update={"runner_preserved": False}))
        return updated, actions

    def _reduce(
        self, position: ManagedPosition, level: str, rr_level: float, reduction_percent: float
    ) -> tuple[ManagedPosition, PartialTakeProfit]:
        reduction_size = position.original_size * reduction_percent / 100.0
        reduction_size = min(position.remaining_size, reduction_size)
        remaining = round(position.remaining_size - reduction_size, 8)
        realized = round(position.realized_rr + rr_level * reduction_size / position.original_size, 4)
        trigger_price = (
            position.entry_price + rr_level * position.initial_risk
            if position.direction == "BUY"
            else position.entry_price - rr_level * position.initial_risk
        )
        updated = position.model_copy(update={"remaining_size": remaining, "realized_rr": realized})
        action = PartialTakeProfit(
            position_id=position.position_id,
            level=level,
            trigger_price=round(trigger_price, 8),
            rr_level=rr_level,
            reduction_percent=round(reduction_size / position.original_size * 100.0, 2),
            remaining_size=remaining,
            realized_rr=realized,
            runner_preserved=remaining > 0,
            reason=f"{level} reached at {rr_level:.1f}R; reduced simulated position exposure.",
        )
        return updated, action

    def _favorable_excursion_rr(self, position: ManagedPosition, candles: list[Any] | None) -> float:
        values: list[float] = []
        for candle in candles or []:
            key = "high" if position.direction == "BUY" else "low"
            value = candle.get(key) if isinstance(candle, dict) else getattr(candle, key, None)
            try:
                values.append(float(value))
            except (TypeError, ValueError):
                continue
        if not values or position.initial_risk <= 0:
            return 0.0
        extreme = max(values) if position.direction == "BUY" else min(values)
        favorable = extreme - position.entry_price if position.direction == "BUY" else position.entry_price - extreme
        return max(0.0, favorable / position.initial_risk)
