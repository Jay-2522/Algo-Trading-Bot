from backend.trade_copier.trade_copier_models import CopySynchronizationSummary, TradeCopyBatch


class CopySynchronizationEngine:
    """Classify copy outcomes without sending, retrying, or modifying orders."""

    def synchronize_batch(self, batch: TradeCopyBatch) -> TradeCopyBatch:
        summary = self.summarize(batch)
        batch.copy_status = summary.synchronization_status
        batch.partial_copy = summary.partial_copy
        batch.warnings = list(dict.fromkeys([*batch.warnings, *summary.warnings]))
        batch.demo_execution = True
        batch.simulation_only = True
        batch.live_execution_enabled = False
        batch.broker_execution_enabled = False
        return batch

    def summarize(self, batch: TradeCopyBatch) -> CopySynchronizationSummary:
        total = len(batch.target_accounts)
        copied = len([result for result in batch.account_copy_results if result.status == "COPIED" or result.copied])
        rejected = len([result for result in batch.account_copy_results if result.status == "REJECTED"])
        unavailable = len([result for result in batch.account_copy_results if result.status == "MT5_UNAVAILABLE"])
        blocked = len(
            [
                result
                for result in batch.account_copy_results
                if result.status in {"BLOCKED", "SKIPPED_DUPLICATE", "FAILED_SAFE"}
            ]
        )
        partial = copied > 0 and copied < total
        warnings = ["Demo trade copier synchronization only. No direct order placement is performed."]
        if partial:
            warnings.append("Partial copy detected across target demo accounts.")
        if unavailable:
            warnings.append("One or more target demo accounts were unavailable during copy coordination.")
        status = self._status(total, copied, rejected, blocked, unavailable, batch.duplicate_blocked)
        return CopySynchronizationSummary(
            copy_batch_id=batch.copy_batch_id,
            total_targets=total,
            copied_count=copied,
            rejected_count=rejected,
            blocked_count=blocked,
            unavailable_count=unavailable,
            partial_copy=partial,
            synchronization_status=status,
            warnings=warnings,
        )

    def _status(
        self,
        total: int,
        copied: int,
        rejected: int,
        blocked: int,
        unavailable: int,
        duplicate_blocked: bool,
    ) -> str:
        if total <= 0:
            return "FAILED_SAFE"
        if copied == total:
            return "COMPLETED"
        if copied > 0:
            return "PARTIAL"
        if duplicate_blocked or blocked == total:
            return "BLOCKED"
        if rejected == total or (rejected > 0 and rejected + blocked + unavailable >= total):
            return "REJECTED"
        if unavailable and unavailable + blocked + rejected >= total:
            return "FAILED_SAFE"
        if copied == 0 and rejected == 0 and blocked == 0 and unavailable == 0:
            return "READY"
        return "IN_PROGRESS"
