from collections import deque
from datetime import datetime, timezone

from backend.execution_queue.execution_queue_models import ExecutionQueueItem


class ExecutionQueueStore:
    """In-memory store for non-executing queue items."""

    def __init__(self, max_items: int = 1000) -> None:
        self.items: deque[ExecutionQueueItem] = deque(maxlen=max_items)

    def add_item(self, item: ExecutionQueueItem) -> ExecutionQueueItem:
        item.simulation_only = True
        item.live_execution_enabled = False
        self.items.appendleft(item)
        return item

    def list_items(self, limit: int = 100) -> list[ExecutionQueueItem]:
        bounded_limit = max(1, min(int(limit), 1000))
        return list(self.items)[:bounded_limit]

    def get_item(self, queue_id: str) -> ExecutionQueueItem | None:
        for item in self.items:
            if item.queue_id == queue_id:
                return item
        return None

    def cancel_item(self, queue_id: str, reason: str) -> ExecutionQueueItem | None:
        item = self.get_item(queue_id)
        if item is None:
            return None
        item.status = "CANCELLED"
        item.readiness = "BLOCKED"
        item.warnings.append(reason or "Queue item cancelled.")
        item.updated_at = datetime.now(timezone.utc)
        item.simulation_only = True
        item.live_execution_enabled = False
        return item
