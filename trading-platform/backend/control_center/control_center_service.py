from typing import Any

from backend.control_center.control_audit_store import ControlAuditStore
from backend.control_center.control_models import ControlAuditEvent, ManualOverrideAction, SafetyControlState
from backend.control_center.manual_override_service import ManualOverrideService
from backend.control_center.safety_lock_manager import SafetyLockManager
from backend.execution_queue.execution_queue_service import ExecutionQueueService
from backend.monitoring.monitoring_service import MonitoringService


class ControlCenterService:
    """Client-facing safety control service for simulation-only operations."""

    def __init__(
        self,
        execution_queue_service: ExecutionQueueService | None = None,
        monitoring_service: MonitoringService | None = None,
    ) -> None:
        self.audit_store = ControlAuditStore()
        self.safety_lock_manager = SafetyLockManager(self.audit_store)
        self.manual_override_service = ManualOverrideService(
            safety_lock_manager=self.safety_lock_manager,
            audit_store=self.audit_store,
            execution_queue_service=execution_queue_service,
            monitoring_service=monitoring_service,
        )

    def get_status(self) -> dict[str, Any]:
        state = self.safety_lock_manager.get_state()
        return {
            "status": "OPERATIONAL",
            "mode": "SIMULATION_ONLY_MANUAL_CONTROLS",
            "queue_paused": state.queue_paused,
            "emergency_stop_active": state.emergency_stop_active,
            "controls_available": [
                "PAUSE_QUEUE",
                "RESUME_QUEUE",
                "CANCEL_QUEUE_ITEM",
                "ACKNOWLEDGE_ALERT",
                "EMERGENCY_STOP_PLACEHOLDER",
            ],
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "message": "Manual controls affect simulated queue state only. Broker execution remains disabled.",
            "timestamp": state.timestamp,
        }

    def get_safety_state(self) -> SafetyControlState:
        return self.safety_lock_manager.get_state()

    def get_audit_events(self, limit: int = 100) -> list[ControlAuditEvent]:
        return self.manual_override_service.get_audit_events(limit)

    def pause_queue(self, reason: str) -> ManualOverrideAction:
        return self.manual_override_service.pause_queue(reason)

    def resume_queue(self, reason: str) -> ManualOverrideAction:
        return self.manual_override_service.resume_queue(reason)

    def cancel_queue_item(self, queue_id: str, reason: str) -> ManualOverrideAction:
        return self.manual_override_service.cancel_queue_item(queue_id, reason)

    def acknowledge_alert(self, alert_id: str, reason: str) -> ManualOverrideAction:
        return self.manual_override_service.acknowledge_alert(alert_id, reason)

    def emergency_stop_placeholder(self, reason: str) -> ManualOverrideAction:
        return self.manual_override_service.emergency_stop_placeholder(reason)
