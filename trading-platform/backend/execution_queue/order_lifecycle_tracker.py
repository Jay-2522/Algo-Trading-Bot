from datetime import datetime, timezone

from backend.execution_queue.execution_lifecycle_models import OrderLifecycleState
from backend.execution_queue.execution_queue_models import ExecutionQueueItem


class OrderLifecycleTracker:
    """Track simulated order lifecycle state transitions."""

    def __init__(self) -> None:
        self.lifecycles: dict[str, OrderLifecycleState] = {}

    def create_lifecycle(self, queue_item: ExecutionQueueItem) -> OrderLifecycleState:
        lifecycle = OrderLifecycleState(
            queue_id=queue_item.queue_id,
            current_state="CREATED",
            history=[self._history("CREATED", "Lifecycle created from queue item.")],
            simulation_only=True,
            live_execution_enabled=False,
        )
        self.lifecycles[queue_item.queue_id] = lifecycle
        return lifecycle

    def update_state(self, queue_id: str, new_state: str, message: str) -> OrderLifecycleState:
        lifecycle = self.lifecycles.get(queue_id)
        if lifecycle is None:
            lifecycle = OrderLifecycleState(queue_id=queue_id, current_state="CREATED")
            self.lifecycles[queue_id] = lifecycle
        lifecycle.current_state = new_state
        lifecycle.updated_at = datetime.now(timezone.utc)
        lifecycle.history.append(self._history(new_state, message))
        lifecycle.simulation_only = True
        lifecycle.live_execution_enabled = False
        return lifecycle

    def get_lifecycle(self, queue_id: str) -> OrderLifecycleState | None:
        return self.lifecycles.get(queue_id)

    def list_lifecycles(self) -> list[OrderLifecycleState]:
        return list(self.lifecycles.values())

    def _history(self, state: str, message: str) -> dict:
        return {"state": state, "message": message, "timestamp": datetime.now(timezone.utc)}
