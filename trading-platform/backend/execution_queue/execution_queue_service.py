from typing import Any

from backend.account_routing.allocation_monitoring_service import AllocationMonitoringService
from backend.execution_queue.execution_lifecycle_models import ExecutionAuditEvent, OrderLifecycleState, SimulatedExecutionResult
from backend.execution_queue.execution_lifecycle_service import ExecutionLifecycleService
from backend.execution_queue.execution_queue_manager import ExecutionQueueManager
from backend.execution_queue.execution_queue_models import ExecutionQueueItem, ExecutionQueueStatus


class ExecutionQueueService:
    """Service facade for execution queue preparation."""

    def __init__(
        self,
        allocation_service: AllocationMonitoringService | None = None,
        queue_manager: ExecutionQueueManager | None = None,
        lifecycle_service: ExecutionLifecycleService | None = None,
    ) -> None:
        self.allocation_service = allocation_service or AllocationMonitoringService()
        self.queue_manager = queue_manager or ExecutionQueueManager()
        self.lifecycle_service = lifecycle_service or ExecutionLifecycleService(self.queue_manager)

    def get_status(self) -> ExecutionQueueStatus:
        return self.queue_manager.get_status()

    def enqueue_preview(self, payload: dict[str, Any]) -> list[ExecutionQueueItem]:
        allocation = self.allocation_service.preview_allocation(payload)
        return self.queue_manager.enqueue_from_allocation(allocation, payload)

    def list_items(self, limit: int = 100) -> list[ExecutionQueueItem]:
        return self.queue_manager.list_queue(limit)

    def get_item(self, queue_id: str) -> ExecutionQueueItem | None:
        return self.queue_manager.get_item(queue_id)

    def cancel_item(self, queue_id: str, reason: str) -> ExecutionQueueItem | None:
        return self.queue_manager.cancel(queue_id, reason)

    def get_lifecycle_status(self) -> dict:
        return self.lifecycle_service.get_status()

    def simulate_queue_item(self, queue_id: str) -> SimulatedExecutionResult | None:
        return self.lifecycle_service.simulate_queue_item(queue_id)

    def simulate_latest(self) -> SimulatedExecutionResult | None:
        return self.lifecycle_service.simulate_latest()

    def get_lifecycles(self) -> list[OrderLifecycleState]:
        return self.lifecycle_service.get_lifecycles()

    def get_audit_events(self, limit: int = 100) -> list[ExecutionAuditEvent]:
        return self.lifecycle_service.get_audit_events(limit)
