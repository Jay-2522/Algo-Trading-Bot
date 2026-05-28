from backend.execution_queue.execution_queue_service import ExecutionQueueService
from backend.monitoring.monitoring_models import ExecutionMonitoringSummary


class ExecutionMonitor:
    """Summarize execution queue and simulated lifecycle activity."""

    def __init__(self, execution_queue_service: ExecutionQueueService | None = None) -> None:
        self.execution_queue_service = execution_queue_service or ExecutionQueueService()

    def generate_execution_summary(self) -> ExecutionMonitoringSummary:
        queue_status = self.execution_queue_service.get_status()
        audit_events = self.execution_queue_service.get_audit_events(1000)
        return ExecutionMonitoringSummary(
            queued_items=queue_status.queued,
            simulated_fills=len([event for event in audit_events if event.event_type == "SIMULATED_FILLED"]),
            simulated_rejections=len([event for event in audit_events if event.event_type == "SIMULATED_REJECTED"]),
            failed_safe=queue_status.failed_safe,
            cancelled=queue_status.cancelled,
        )
