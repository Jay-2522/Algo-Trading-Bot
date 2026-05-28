from datetime import datetime, timezone

from backend.control_center.control_audit_store import ControlAuditStore
from backend.control_center.control_models import ManualOverrideAction, SafetyControlState


class SafetyLockManager:
    """Manage dashboard safety locks without enabling any execution pathway."""

    def __init__(self, audit_store: ControlAuditStore | None = None) -> None:
        self.audit_store = audit_store or ControlAuditStore()
        self.queue_paused = False
        self.emergency_stop_active = False
        self.active_locks: set[str] = set()

    def get_state(self) -> SafetyControlState:
        state = SafetyControlState(
            queue_paused=self.queue_paused,
            emergency_stop_active=self.emergency_stop_active,
            live_execution_enabled=False,
            broker_execution_enabled=False,
            simulation_only=True,
            active_locks=sorted(self.active_locks),
            timestamp=datetime.now(timezone.utc),
        )
        self.audit_store.log_event(
            "SAFETY_STATUS_CHECK",
            "Dashboard safety state checked.",
            {
                "queue_paused": state.queue_paused,
                "emergency_stop_active": state.emergency_stop_active,
                "simulation_only": True,
                "live_execution_enabled": False,
            },
        )
        return state

    def pause_queue(self, reason: str) -> ManualOverrideAction:
        self.queue_paused = True
        self.active_locks.add("QUEUE_PAUSED")
        action = ManualOverrideAction(
            action_type="PAUSE_QUEUE",
            reason=reason or "Simulation queue paused from dashboard.",
            accepted=True,
            message="Simulation queue paused. No live broker execution is enabled.",
            simulation_only=True,
            live_execution_enabled=False,
        )
        self.audit_store.log_event(action.action_type, action.reason, action.model_dump(mode="json"))
        return action

    def resume_queue(self, reason: str) -> ManualOverrideAction:
        self.queue_paused = False
        self.active_locks.discard("QUEUE_PAUSED")
        action = ManualOverrideAction(
            action_type="RESUME_QUEUE",
            reason=reason or "Simulation queue resumed from dashboard.",
            accepted=True,
            message="Simulation queue resumed for preview processing only.",
            simulation_only=True,
            live_execution_enabled=False,
        )
        self.audit_store.log_event(action.action_type, action.reason, action.model_dump(mode="json"))
        return action

    def emergency_stop_placeholder(self, reason: str) -> ManualOverrideAction:
        self.emergency_stop_active = True
        self.active_locks.add("EMERGENCY_STOP_PLACEHOLDER")
        action = ManualOverrideAction(
            action_type="EMERGENCY_STOP_PLACEHOLDER",
            reason=reason or "Emergency stop placeholder activated from dashboard.",
            accepted=True,
            message="Emergency stop placeholder recorded. Live execution remains unavailable and disabled.",
            simulation_only=True,
            live_execution_enabled=False,
        )
        self.audit_store.log_event(action.action_type, action.reason, action.model_dump(mode="json"))
        return action
