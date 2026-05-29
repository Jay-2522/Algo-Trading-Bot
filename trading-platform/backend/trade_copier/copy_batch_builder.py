from typing import Any

from backend.multi_account_execution.account_execution_planner import AccountExecutionPlanner
from backend.multi_account_execution.multi_account_models import MultiAccountDemoExecutionResult
from backend.replay.symbol_normalizer import SymbolNormalizer
from backend.trade_copier.trade_copier_models import AccountCopyStatus, TradeCopyBatch


class CopyBatchBuilder:
    """Build auditable demo trade copy batches from signals or Day 3 results."""

    def __init__(
        self,
        planner: AccountExecutionPlanner | None = None,
        normalizer: SymbolNormalizer | None = None,
    ) -> None:
        self.planner = planner or AccountExecutionPlanner()
        self.normalizer = normalizer or SymbolNormalizer()

    def build_from_multi_account_result(self, multi_account_result: MultiAccountDemoExecutionResult) -> TradeCopyBatch:
        account_results = [
            AccountCopyStatus(
                account_id=result.account_id,
                broker_id=result.broker_id,
                status=self._status_from_execution_result(result.status),
                mt5_retcode=result.mt5_retcode,
                mt5_order=result.mt5_order,
                mt5_deal=result.mt5_deal,
                rejection_reasons=result.rejection_reasons,
                copied=result.status == "DEMO_FILLED",
            )
            for result in multi_account_result.account_results
        ]
        batch = TradeCopyBatch(
            source_signal_id=multi_account_result.signal_id,
            canonical_symbol=multi_account_result.canonical_symbol,
            action=multi_account_result.action,
            target_accounts=[result.account_id for result in account_results],
            account_copy_results=account_results,
            warnings=list(multi_account_result.warnings),
            demo_execution=True,
            simulation_only=True,
            live_execution_enabled=False,
            broker_execution_enabled=False,
        )
        if multi_account_result.canonical_symbol != "EURUSD":
            self._block_batch(batch, f"{multi_account_result.canonical_symbol} is blocked. Demo trade copier allows EURUSD only.")
        return batch

    def build_from_signal(self, signal_payload: dict[str, Any]) -> TradeCopyBatch:
        plans = self.planner.build_plans(signal_payload)
        symbol = plans[0].canonical_symbol if plans else self.normalizer.normalize(signal_payload.get("canonical_symbol") or signal_payload.get("symbol"))
        action = plans[0].action if plans else str(signal_payload.get("action") or "").upper()
        signal_id = str(signal_payload.get("signal_id") or "trade-copy-demo")
        blocked_symbol = symbol != "EURUSD"
        account_results: list[AccountCopyStatus] = []

        for plan in plans:
            reasons = list(plan.rejection_reasons)
            status = "BLOCKED" if reasons or blocked_symbol else "PLANNED"
            if blocked_symbol and not any("EURUSD" in reason for reason in reasons):
                reasons.append(f"{symbol} is blocked. Demo trade copier allows EURUSD only.")
            account_results.append(
                AccountCopyStatus(
                    account_id=plan.account_id,
                    broker_id=plan.broker_id,
                    status=status,
                    rejection_reasons=reasons,
                    copied=False,
                )
            )

        batch = TradeCopyBatch(
            source_signal_id=signal_id,
            canonical_symbol=symbol,
            action=action,
            target_accounts=[plan.account_id for plan in plans],
            copy_status="BLOCKED" if blocked_symbol else "READY",
            account_copy_results=account_results,
            warnings=["Demo trade copier coordination only. Live and broker execution remain disabled."],
            demo_execution=True,
            simulation_only=True,
            live_execution_enabled=False,
            broker_execution_enabled=False,
        )
        if blocked_symbol:
            self._block_batch(batch, f"{symbol} is blocked. Demo trade copier allows EURUSD only.")
        return batch

    def _status_from_execution_result(self, status: str) -> str:
        return {
            "DEMO_FILLED": "COPIED",
            "DEMO_REJECTED": "REJECTED",
            "BLOCKED": "BLOCKED",
            "SKIPPED_DUPLICATE": "SKIPPED_DUPLICATE",
            "MT5_UNAVAILABLE": "MT5_UNAVAILABLE",
            "FAILED_SAFE": "FAILED_SAFE",
        }.get(status, "FAILED_SAFE")

    def _block_batch(self, batch: TradeCopyBatch, reason: str) -> None:
        batch.copy_status = "BLOCKED"
        batch.partial_copy = False
        if reason not in batch.warnings:
            batch.warnings.append(reason)
        for result in batch.account_copy_results:
            result.status = "BLOCKED"
            result.copied = False
            if reason not in result.rejection_reasons:
                result.rejection_reasons.append(reason)
