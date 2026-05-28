from typing import Any

from backend.account_routing.allocation_models import AllocationDecision
from backend.execution_queue.execution_intent_builder import ExecutionIntentBuilder
from backend.execution_queue.execution_queue_models import ExecutionQueueItem, ExecutionQueueStatus
from backend.execution_queue.execution_queue_store import ExecutionQueueStore
from backend.execution_queue.execution_readiness_validator import ExecutionReadinessValidator


class ExecutionQueueManager:
    """Manage non-executing queue items derived from allocation previews."""

    def __init__(
        self,
        intent_builder: ExecutionIntentBuilder | None = None,
        validator: ExecutionReadinessValidator | None = None,
        store: ExecutionQueueStore | None = None,
    ) -> None:
        self.intent_builder = intent_builder or ExecutionIntentBuilder()
        self.validator = validator or ExecutionReadinessValidator()
        self.store = store or ExecutionQueueStore()

    def enqueue_from_allocation(
        self,
        allocation_decision: AllocationDecision,
        signal_payload: dict[str, Any] | None = None,
    ) -> list[ExecutionQueueItem]:
        items: list[ExecutionQueueItem] = []
        intents = self.intent_builder.build_intents_from_allocation(allocation_decision, signal_payload)
        for intent in intents:
            readiness, errors, warnings = self.validator.validate_intent(intent)
            status = "QUEUED" if readiness == "READY_FOR_DEMO_QUEUE" else "HELD" if readiness == "WAITING_FOR_CONFIRMATION" else "FAILED_SAFE"
            item = ExecutionQueueItem(
                intent=intent,
                status=status,
                readiness=readiness,
                validation_errors=errors,
                warnings=warnings,
                simulation_only=True,
                live_execution_enabled=False,
            )
            items.append(self.store.add_item(item))
        return items

    def cancel(self, queue_id: str, reason: str) -> ExecutionQueueItem | None:
        return self.store.cancel_item(queue_id, reason)

    def get_status(self) -> ExecutionQueueStatus:
        items = self.store.list_items(1000)
        return ExecutionQueueStatus(
            total_items=len(items),
            queued=len([item for item in items if item.status == "QUEUED"]),
            held=len([item for item in items if item.status == "HELD"]),
            cancelled=len([item for item in items if item.status == "CANCELLED"]),
            failed_safe=len([item for item in items if item.status == "FAILED_SAFE"]),
            execution_disabled=len([item for item in items if item.status == "EXECUTION_DISABLED"]),
            simulation_only=True,
            live_execution_enabled=False,
        )

    def list_queue(self, limit: int = 100) -> list[ExecutionQueueItem]:
        return self.store.list_items(limit)

    def get_item(self, queue_id: str) -> ExecutionQueueItem | None:
        return self.store.get_item(queue_id)
