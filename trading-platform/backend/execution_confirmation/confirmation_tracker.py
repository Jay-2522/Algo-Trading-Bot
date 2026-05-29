from collections import deque
from typing import Any

from backend.execution_confirmation.confirmation_audit_store import ConfirmationAuditStore
from backend.execution_confirmation.confirmation_models import ExecutionConfirmation


class ExecutionConfirmationTracker:
    """Track execution confirmations from existing demo execution result objects."""

    def __init__(self, audit_store: ConfirmationAuditStore | None = None, max_confirmations: int = 1000) -> None:
        self.audit_store = audit_store or ConfirmationAuditStore()
        self.confirmations: deque[ExecutionConfirmation] = deque(maxlen=max_confirmations)

    def track_execution(self, result: Any) -> list[ExecutionConfirmation] | ExecutionConfirmation:
        if hasattr(result, "account_results"):
            return [self._store(self._from_multi_account_result(result, account_result)) for account_result in result.account_results]
        return self._store(self._from_demo_result(result))

    def get_confirmation(self, execution_id: str) -> ExecutionConfirmation | None:
        for confirmation in self.confirmations:
            if confirmation.execution_id == execution_id:
                return confirmation
        return None

    def list_confirmations(self, limit: int = 100) -> list[ExecutionConfirmation]:
        bounded_limit = max(1, min(int(limit), 1000))
        return list(self.confirmations)[:bounded_limit]

    def update_confirmation(self, record: ExecutionConfirmation) -> ExecutionConfirmation:
        self._force_safety_flags(record)
        for index, stored in enumerate(self.confirmations):
            if stored.execution_id == record.execution_id:
                self.confirmations[index] = record
                return record
        self.confirmations.appendleft(record)
        return record

    def _store(self, record: ExecutionConfirmation) -> ExecutionConfirmation:
        existing = self.get_confirmation(record.execution_id)
        if existing is not None:
            return existing
        self._force_safety_flags(record)
        self.confirmations.appendleft(record)
        self.audit_store.store_event(
            "CONFIRMATION_CREATED",
            "Execution confirmation record created from existing demo result.",
            record.execution_id,
            record.model_dump(mode="json"),
        )
        return record

    def _from_demo_result(self, result: Any) -> ExecutionConfirmation:
        status = str(getattr(result, "status", "") or "")
        order = getattr(result, "mt5_order", None)
        deal = getattr(result, "mt5_deal", None)
        rejected = status in {"DEMO_REJECTED", "BLOCKED", "FAILED_SAFE", "MT5_UNAVAILABLE"}
        return ExecutionConfirmation(
            execution_id=str(getattr(result, "execution_id", None) or getattr(result, "queue_id", "unknown_execution")),
            signal_id=str(getattr(result, "queue_id", "") or ""),
            account_id=getattr(result, "account_id", None),
            broker_id=getattr(result, "broker_id", None),
            canonical_symbol=getattr(result, "canonical_symbol", None),
            action=getattr(result, "action", None),
            mt5_order=order,
            mt5_deal=deal,
            mt5_retcode=getattr(result, "mt5_retcode", None),
            order_confirmed=order is not None,
            deal_confirmed=deal is not None,
            position_detected=order is not None and deal is not None and status == "DEMO_FILLED",
            reconciliation_status="REJECTED" if rejected else "PENDING",
            warnings=list(getattr(result, "warnings", []) or getattr(result, "rejection_reasons", []) or []),
            simulation_only=True,
            demo_execution=True,
            live_execution_enabled=False,
            broker_execution_enabled=False,
        )

    def _from_multi_account_result(self, batch: Any, account_result: Any) -> ExecutionConfirmation:
        status = str(getattr(account_result, "status", "") or "")
        order = getattr(account_result, "mt5_order", None)
        deal = getattr(account_result, "mt5_deal", None)
        rejected = status in {"DEMO_REJECTED", "BLOCKED", "SKIPPED_DUPLICATE", "MT5_UNAVAILABLE", "FAILED_SAFE"}
        return ExecutionConfirmation(
            execution_id=f"{getattr(batch, 'batch_id', 'multi_batch')}:{getattr(account_result, 'account_id', 'account')}",
            signal_id=getattr(batch, "signal_id", None),
            account_id=getattr(account_result, "account_id", None),
            broker_id=getattr(account_result, "broker_id", None),
            canonical_symbol=getattr(batch, "canonical_symbol", None),
            action=getattr(batch, "action", None),
            mt5_order=order,
            mt5_deal=deal,
            mt5_retcode=getattr(account_result, "mt5_retcode", None),
            order_confirmed=order is not None,
            deal_confirmed=deal is not None,
            position_detected=order is not None and deal is not None and status == "DEMO_FILLED",
            reconciliation_status="REJECTED" if rejected else "PENDING",
            warnings=list(getattr(account_result, "rejection_reasons", []) or []),
            simulation_only=True,
            demo_execution=True,
            live_execution_enabled=False,
            broker_execution_enabled=False,
        )

    def _force_safety_flags(self, record: ExecutionConfirmation) -> None:
        record.simulation_only = True
        record.demo_execution = True
        record.live_execution_enabled = False
        record.broker_execution_enabled = False
