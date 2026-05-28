from typing import Any

from backend.control_center.control_audit_store import ControlAuditStore
from backend.control_center.control_models import ControlAuditEvent, ManualOverrideAction
from backend.control_center.safety_lock_manager import SafetyLockManager
from backend.execution_queue.execution_queue_service import ExecutionQueueService
from backend.monitoring.monitoring_service import MonitoringService


class ManualOverrideService:
    """Simulation-only operator override facade for dashboard controls."""

    def __init__(
        self,
        safety_lock_manager: SafetyLockManager | None = None,
        audit_store: ControlAuditStore | None = None,
        execution_queue_service: ExecutionQueueService | None = None,
        monitoring_service: MonitoringService | None = None,
    ) -> None:
        self.audit_store = audit_store or ControlAuditStore()
        self.safety_lock_manager = safety_lock_manager or SafetyLockManager(self.audit_store)
        self.execution_queue_service = execution_queue_service or ExecutionQueueService()
        self.monitoring_service = monitoring_service or MonitoringService()

    def pause_queue(self, reason: str) -> ManualOverrideAction:
        return self.safety_lock_manager.pause_queue(reason)

    def resume_queue(self, reason: str) -> ManualOverrideAction:
        return self.safety_lock_manager.resume_queue(reason)

    def cancel_queue_item(self, queue_id: str, reason: str) -> ManualOverrideAction:
        item = self.execution_queue_service.cancel_item(queue_id, reason or "Cancelled from manual control panel.")
        accepted = item is not None
        action = ManualOverrideAction(
            action_type="CANCEL_QUEUE_ITEM",
            reason=reason or "Cancelled from manual control panel.",
            accepted=accepted,
            message=(
                "Queued simulation item cancelled. No broker order was touched."
                if accepted
                else "Queue item was not found; no execution action was taken."
            ),
            simulation_only=True,
            live_execution_enabled=False,
        )
        result: dict[str, Any] = action.model_dump(mode="json")
        result["queue_id"] = queue_id
        result["item_found"] = accepted
        self.audit_store.log_event(action.action_type, action.reason, result)
        return action

    def acknowledge_alert(self, alert_id: str, reason: str = "Acknowledged from manual control panel.") -> ManualOverrideAction:
        alert = self.monitoring_service.acknowledge_alert(alert_id)
        accepted = alert is not None
        action = ManualOverrideAction(
            action_type="ACKNOWLEDGE_ALERT",
            reason=reason,
            accepted=accepted,
            message=(
                "Monitoring alert acknowledged."
                if accepted
                else "Alert was not found; acknowledgement was recorded as a safe no-op."
            ),
            simulation_only=True,
            live_execution_enabled=False,
        )
        result: dict[str, Any] = action.model_dump(mode="json")
        result["alert_id"] = alert_id
        result["alert_found"] = accepted
        self.audit_store.log_event(action.action_type, action.reason, result)
        return action

    def emergency_stop_placeholder(self, reason: str) -> ManualOverrideAction:
        return self.safety_lock_manager.emergency_stop_placeholder(reason)

    def get_audit_events(self, limit: int = 100) -> list[ControlAuditEvent]:
        return self.audit_store.get_recent_events(limit)
