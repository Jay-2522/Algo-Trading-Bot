from backend.institutional_intelligence.position_management_models import ManagedPosition, PositionState


class PositionStateMachine:
    """Enforce auditable deterministic transitions for simulation position management."""

    ALLOWED: dict[str, set[str]] = {
        "PENDING": {"ACTIVE"},
        "ACTIVE": {"PARTIAL_TP_1", "CLOSING", "CLOSED"},
        "PARTIAL_TP_1": {"BREAK_EVEN", "CLOSING", "CLOSED"},
        "BREAK_EVEN": {"TRAILING", "CLOSING", "CLOSED"},
        "TRAILING": {"PARTIAL_TP_2", "CLOSING", "CLOSED"},
        "PARTIAL_TP_2": {"TRAILING", "CLOSING", "CLOSED"},
        "CLOSING": {"CLOSED"},
        "CLOSED": set(),
        "INVALIDATED": set(),
        "EMERGENCY_EXIT": set(),
    }

    def transition(self, position: ManagedPosition, new_state: str, reason: str) -> tuple[ManagedPosition, PositionState]:
        previous = position.state
        emergency = new_state in {"EMERGENCY_EXIT", "INVALIDATED"}
        if not emergency and new_state not in self.ALLOWED.get(previous, set()):
            raise ValueError(f"Invalid management transition: {previous} -> {new_state}")
        updated = position.model_copy(update={"state": new_state})
        return updated, PositionState(
            position_id=position.position_id,
            previous_state=previous,
            state=new_state,
            reason=reason,
        )
