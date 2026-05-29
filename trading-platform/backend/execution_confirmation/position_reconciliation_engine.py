from backend.execution_confirmation.confirmation_audit_store import ConfirmationAuditStore
from backend.execution_confirmation.confirmation_models import ExecutionConfirmation, ReconciliationSummary
from backend.execution_confirmation.confirmation_tracker import ExecutionConfirmationTracker


class PositionReconciliationEngine:
    """Read-only reconciliation of order, deal, and position confirmation state."""

    def __init__(
        self,
        tracker: ExecutionConfirmationTracker | None = None,
        audit_store: ConfirmationAuditStore | None = None,
    ) -> None:
        self.audit_store = audit_store or ConfirmationAuditStore()
        self.tracker = tracker or ExecutionConfirmationTracker(audit_store=self.audit_store)

    def reconcile_confirmation(self, record: ExecutionConfirmation) -> ExecutionConfirmation:
        previous_status = record.reconciliation_status
        record.reconciliation_status = self._classify(record)
        record.simulation_only = True
        record.demo_execution = True
        record.live_execution_enabled = False
        record.broker_execution_enabled = False
        self._audit(record, previous_status)
        return self.tracker.update_confirmation(record)

    def reconcile_all(self) -> list[ExecutionConfirmation]:
        return [self.reconcile_confirmation(record) for record in self.tracker.list_confirmations(1000)]

    def build_summary(self) -> ReconciliationSummary:
        records = self.tracker.list_confirmations(1000)
        warnings = ["Execution confirmation reconciliation is read-only and demo-only."]
        if any(record.reconciliation_status == "MISSING_POSITION" for record in records):
            warnings.append("One or more executions have an order/deal confirmation without a detected position.")
        if any(record.reconciliation_status == "MISMATCHED" for record in records):
            warnings.append("One or more executions have inconsistent order, deal, or position data.")
        return ReconciliationSummary(
            total_executions=len(records),
            confirmed=len([record for record in records if record.reconciliation_status == "CONFIRMED"]),
            pending=len([record for record in records if record.reconciliation_status == "PENDING"]),
            rejected=len([record for record in records if record.reconciliation_status in {"REJECTED", "FAILED_SAFE"}]),
            missing_position=len([record for record in records if record.reconciliation_status == "MISSING_POSITION"]),
            mismatched=len([record for record in records if record.reconciliation_status == "MISMATCHED"]),
            warnings=warnings,
            simulation_only=True,
            demo_execution=True,
            live_execution_enabled=False,
            broker_execution_enabled=False,
        )

    def _classify(self, record: ExecutionConfirmation) -> str:
        if record.reconciliation_status == "REJECTED" or self._retcode_rejected(record.mt5_retcode):
            return "REJECTED"
        if record.order_confirmed and record.deal_confirmed and record.position_detected:
            return "CONFIRMED"
        if record.order_confirmed and record.deal_confirmed and not record.position_detected:
            return "MISSING_POSITION"
        if record.position_detected and not (record.order_confirmed and record.deal_confirmed):
            return "MISMATCHED"
        if record.order_confirmed != (record.mt5_order is not None) or record.deal_confirmed != (record.mt5_deal is not None):
            return "MISMATCHED"
        if not record.order_confirmed and not record.deal_confirmed and record.mt5_retcode is None:
            return "PENDING"
        if record.mt5_retcode is not None and not record.order_confirmed and not record.deal_confirmed:
            return "REJECTED"
        return "PENDING"

    def _retcode_rejected(self, retcode: int | str | None) -> bool:
        if retcode is None:
            return False
        normalized = str(retcode).upper()
        return any(marker in normalized for marker in ("REJECT", "INVALID", "DENIED", "ERROR", "FAILED"))

    def _audit(self, record: ExecutionConfirmation, previous_status: str) -> None:
        if record.reconciliation_status == "CONFIRMED":
            self.audit_store.store_event("CONFIRMATION_CONFIRMED", "Execution order, deal, and position are confirmed.", record.execution_id)
            self.audit_store.store_event("POSITION_RECONCILED", "Position lifecycle reconciled.", record.execution_id)
        elif record.reconciliation_status == "REJECTED":
            self.audit_store.store_event("CONFIRMATION_REJECTED", "Execution confirmation reconciled as rejected.", record.execution_id)
        elif record.reconciliation_status == "MISSING_POSITION":
            self.audit_store.store_event("POSITION_MISSING", "Order/deal confirmation exists but position is missing.", record.execution_id)
        elif record.reconciliation_status == "MISMATCHED":
            self.audit_store.store_event("RECONCILIATION_MISMATCH", "Execution confirmation data is inconsistent.", record.execution_id)
        elif previous_status != record.reconciliation_status:
            self.audit_store.store_event("POSITION_RECONCILED", "Execution confirmation remains pending.", record.execution_id)
