from typing import Any

from backend.trade_copier.copy_batch_builder import CopyBatchBuilder
from backend.trade_copier.copy_duplicate_guard import CopyDuplicateGuard
from backend.trade_copier.copy_status_tracker import CopyStatusTracker
from backend.trade_copier.copy_synchronization_engine import CopySynchronizationEngine
from backend.trade_copier.trade_copier_models import CopySynchronizationSummary, TradeCopyBatch
from backend.execution_risk.execution_risk_evaluator import ExecutionRiskEvaluator


class TradeCopierService:
    """Facade for safe demo trade-copy coordination."""

    def __init__(
        self,
        builder: CopyBatchBuilder | None = None,
        synchronizer: CopySynchronizationEngine | None = None,
        tracker: CopyStatusTracker | None = None,
        duplicate_guard: CopyDuplicateGuard | None = None,
        risk_evaluator: ExecutionRiskEvaluator | None = None,
    ) -> None:
        self.builder = builder or CopyBatchBuilder()
        self.synchronizer = synchronizer or CopySynchronizationEngine()
        self.tracker = tracker or CopyStatusTracker()
        self.duplicate_guard = duplicate_guard or CopyDuplicateGuard()
        self.risk_evaluator = risk_evaluator or ExecutionRiskEvaluator()

    def get_status(self) -> dict[str, Any]:
        return {
            "status": "OPERATIONAL",
            "mode": "DEMO_TRADE_COPIER_COORDINATION_ONLY",
            "allowed_symbol": "EURUSD",
            "blocked_symbols": ["XAUUSD", "NIFTY50"],
            "max_lot_per_account": 0.01,
            "target_accounts": ["STARTRADER_DEMO_1", "FXPRO_DEMO_1", "VANTAGE_DEMO_1"],
            "demo_execution": True,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "duplicate_guard_enabled": True,
        }

    def preview_copy(self, signal_payload: dict[str, Any]) -> TradeCopyBatch:
        return self.builder.build_from_signal(signal_payload)

    def create_copy_batch(self, signal_payload: dict[str, Any]) -> TradeCopyBatch:
        batch = self.builder.build_from_signal(signal_payload)
        self._apply_risk_guard(batch, signal_payload)
        self._apply_duplicate_guard(batch, mark_new=batch.copy_status != "BLOCKED")
        return self.tracker.store_batch(batch)

    def synchronize_batch(self, copy_batch_id: str) -> CopySynchronizationSummary | None:
        batch = self.tracker.get_batch(copy_batch_id)
        if batch is None:
            return None
        synchronized = self.synchronizer.synchronize_batch(batch)
        self.tracker.update_batch(synchronized)
        return self.synchronizer.summarize(synchronized)

    def list_batches(self, limit: int = 100) -> list[TradeCopyBatch]:
        return self.tracker.list_batches(limit)

    def get_batch(self, copy_batch_id: str) -> TradeCopyBatch | None:
        return self.tracker.get_batch(copy_batch_id)

    def _apply_duplicate_guard(self, batch: TradeCopyBatch, mark_new: bool) -> None:
        for result in batch.account_copy_results:
            duplicate = self.duplicate_guard.is_duplicate(
                batch.source_signal_id,
                result.account_id,
                batch.canonical_symbol,
                batch.action,
            ) or self._has_existing_copy_key(batch, result.account_id)
            if duplicate:
                result.status = "SKIPPED_DUPLICATE"
                result.copied = False
                batch.duplicate_blocked = True
                reason = "Duplicate trade copy attempt for this signal/account/symbol/action is blocked."
                if reason not in result.rejection_reasons:
                    result.rejection_reasons.append(reason)
                if reason not in batch.warnings:
                    batch.warnings.append(reason)
                continue
            if mark_new and result.status in {"PLANNED", "COPIED"}:
                self.duplicate_guard.mark_copied(
                    batch.source_signal_id,
                    result.account_id,
                    batch.canonical_symbol,
                    batch.action,
                )
        if batch.duplicate_blocked and all(result.status == "SKIPPED_DUPLICATE" for result in batch.account_copy_results):
            batch.copy_status = "BLOCKED"

    def _has_existing_copy_key(self, batch: TradeCopyBatch, account_id: str) -> bool:
        for stored in self.tracker.list_batches(limit=1000):
            if stored.source_signal_id != batch.source_signal_id:
                continue
            if stored.canonical_symbol != batch.canonical_symbol:
                continue
            if stored.action != batch.action:
                continue
            if any(result.account_id == account_id for result in stored.account_copy_results):
                return True
        return False

    def _apply_risk_guard(self, batch: TradeCopyBatch, signal_payload: dict[str, Any]) -> None:
        for result in batch.account_copy_results:
            decision = self.risk_evaluator.evaluate_copy_request(
                {
                    "request_type": "copy",
                    "request_id": batch.source_signal_id,
                    "canonical_symbol": batch.canonical_symbol,
                    "action": batch.action,
                    "account_id": result.account_id,
                    "broker_id": result.broker_id,
                    "lot": signal_payload.get("lot") or 0.01,
                    "target_account_count": len(batch.target_accounts),
                    "confirm_demo_execution": bool(signal_payload.get("confirm_demo_execution", True)),
                    "live_execution_enabled": False,
                    "broker_execution_enabled": False,
                }
            )
            if decision.approved:
                continue
            result.status = "BLOCKED"
            result.copied = False
            batch.copy_status = "BLOCKED"
            for reason in decision.rejection_reasons:
                message = f"Execution risk blocked: {reason}"
                if message not in result.rejection_reasons:
                    result.rejection_reasons.append(message)
                if message not in batch.warnings:
                    batch.warnings.append(message)
