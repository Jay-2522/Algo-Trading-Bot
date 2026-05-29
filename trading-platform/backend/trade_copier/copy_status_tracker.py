from collections import deque

from backend.trade_copier.trade_copier_models import TradeCopyBatch


class CopyStatusTracker:
    """In-memory audit tracker for demo trade copy batches."""

    def __init__(self, max_batches: int = 1000) -> None:
        self.batches: deque[TradeCopyBatch] = deque(maxlen=max_batches)

    def store_batch(self, batch: TradeCopyBatch) -> TradeCopyBatch:
        self._force_safety_flags(batch)
        self.batches.appendleft(batch)
        return batch

    def list_batches(self, limit: int = 100) -> list[TradeCopyBatch]:
        bounded_limit = max(1, min(int(limit), 1000))
        return list(self.batches)[:bounded_limit]

    def get_batch(self, copy_batch_id: str) -> TradeCopyBatch | None:
        for batch in self.batches:
            if batch.copy_batch_id == copy_batch_id:
                return batch
        return None

    def update_batch(self, batch: TradeCopyBatch) -> TradeCopyBatch:
        self._force_safety_flags(batch)
        for index, stored in enumerate(self.batches):
            if stored.copy_batch_id == batch.copy_batch_id:
                self.batches[index] = batch
                return batch
        self.batches.appendleft(batch)
        return batch

    def _force_safety_flags(self, batch: TradeCopyBatch) -> None:
        batch.demo_execution = True
        batch.simulation_only = True
        batch.live_execution_enabled = False
        batch.broker_execution_enabled = False
