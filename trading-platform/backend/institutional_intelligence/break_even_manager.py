from backend.institutional_intelligence.position_management_models import BreakEvenAdjustment, ManagedPosition


class BreakEvenManager:
    """Protect initial capital after TP1 without ever widening the simulated stop."""

    def apply_break_even(self, position: ManagedPosition) -> tuple[ManagedPosition, BreakEvenAdjustment]:
        improves_stop = (
            position.current_stop < position.entry_price
            if position.direction == "BUY"
            else position.current_stop > position.entry_price
        )
        applied = position.tp1_achieved and not position.break_even_applied and improves_stop
        new_stop = position.entry_price if applied else position.current_stop
        adjustment = BreakEvenAdjustment(
            position_id=position.position_id,
            applied=applied,
            previous_stop=position.current_stop,
            adjusted_stop=new_stop,
            protected_rr=0.0,
            reason="Stop moved to entry after TP1." if applied else "Break-even move not required or would not improve protection.",
        )
        if not applied:
            return position, adjustment
        return position.model_copy(update={"current_stop": new_stop, "break_even_applied": True}), adjustment
