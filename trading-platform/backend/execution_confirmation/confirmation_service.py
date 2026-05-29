from typing import Any

from backend.execution_confirmation.confirmation_audit_store import ConfirmationAuditStore
from backend.execution_confirmation.confirmation_models import ExecutionConfirmation, ReconciliationSummary
from backend.execution_confirmation.confirmation_tracker import ExecutionConfirmationTracker
from backend.execution_confirmation.position_reconciliation_engine import PositionReconciliationEngine


class ExecutionConfirmationService:
    """Service facade for demo execution confirmation tracking and reconciliation."""

    def __init__(
        self,
        tracker: ExecutionConfirmationTracker | None = None,
        reconciliation_engine: PositionReconciliationEngine | None = None,
        audit_store: ConfirmationAuditStore | None = None,
        demo_result_store: Any | None = None,
        multi_account_result_store: Any | None = None,
    ) -> None:
        self.audit_store = audit_store or ConfirmationAuditStore()
        self.tracker = tracker or ExecutionConfirmationTracker(audit_store=self.audit_store)
        self.reconciliation_engine = reconciliation_engine or PositionReconciliationEngine(
            tracker=self.tracker,
            audit_store=self.audit_store,
        )
        self.demo_result_store = demo_result_store
        self.multi_account_result_store = multi_account_result_store
        self._ingested_result_keys: set[str] = set()

    def get_status(self) -> dict[str, Any]:
        self._ingest_existing_results()
        return {
            "status": "OPERATIONAL",
            "mode": "DEMO_EXECUTION_CONFIRMATION_TRACKING_ONLY",
            "tracked_confirmations": len(self.tracker.list_confirmations(1000)),
            "read_only_mt5_inspection_allowed": True,
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def list_confirmations(self, limit: int = 100) -> list[ExecutionConfirmation]:
        self._ingest_existing_results()
        return self.tracker.list_confirmations(limit)

    def get_confirmation(self, execution_id: str) -> ExecutionConfirmation | None:
        self._ingest_existing_results()
        return self.tracker.get_confirmation(execution_id)

    def reconcile_all(self) -> list[ExecutionConfirmation]:
        self._ingest_existing_results()
        return self.reconciliation_engine.reconcile_all()

    def reconciliation_summary(self) -> ReconciliationSummary:
        self._ingest_existing_results()
        return self.reconciliation_engine.build_summary()

    def audit_events(self, limit: int = 100) -> list[Any]:
        return self.audit_store.list_events(limit)

    def _ingest_existing_results(self) -> None:
        for result in self._list_store_results(self.demo_result_store):
            key = f"demo:{getattr(result, 'execution_id', id(result))}"
            if key not in self._ingested_result_keys:
                self.tracker.track_execution(result)
                self._ingested_result_keys.add(key)
        for result in self._list_store_results(self.multi_account_result_store):
            key = f"multi:{getattr(result, 'batch_id', id(result))}"
            if key not in self._ingested_result_keys:
                self.tracker.track_execution(result)
                self._ingested_result_keys.add(key)

    def _list_store_results(self, store: Any | None) -> list[Any]:
        if store is None:
            return []
        if hasattr(store, "list_results"):
            return list(store.list_results(1000))
        return []
