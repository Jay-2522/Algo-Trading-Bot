from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from backend.trade_copier.copier_execution_store import CopierExecutionStore
from backend.trade_copier.trade_copier_service import TradeCopierService


CopyExecutionStatus = Literal["COPIED", "PARTIAL_COPY", "DUPLICATE_BLOCKED", "FAILED_SAFE"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TradeCopierExecutionResult(BaseModel):
    copier_execution_id: str = Field(default_factory=lambda: f"copier_exec_{uuid4().hex[:12]}")
    source_execution_id: str | None = None
    source_signal_id: str | None = None
    source_symbol: str | None = None
    source_action: str | None = None
    source_lot: float = 0.0
    copy_batch_id: str | None = None
    copied_accounts: list[str] = Field(default_factory=list)
    skipped_accounts: list[str] = Field(default_factory=list)
    failed_accounts: list[str] = Field(default_factory=list)
    duplicate_blocked: bool = False
    copy_status: CopyExecutionStatus = "FAILED_SAFE"
    simulation_only: bool = True
    demo_execution: bool = True
    live_execution_enabled: bool = False
    broker_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)

    def model_post_init(self, __context: Any) -> None:
        self.simulation_only = True
        self.demo_execution = True
        self.live_execution_enabled = False
        self.broker_execution_enabled = False


class CopierExecutionBridge:
    """Bridge completed demo execution records into the existing trade copier."""

    ALLOWED_SYMBOL = "EURUSD"

    def __init__(
        self,
        trade_copier_service: TradeCopierService | None = None,
        store: CopierExecutionStore | None = None,
    ) -> None:
        self.trade_copier_service = trade_copier_service or TradeCopierService()
        self.store = store or CopierExecutionStore()

    def create_copy_batch_from_execution(self, execution: Any):
        payload = self._payload_from_execution(execution)
        return self.trade_copier_service.create_copy_batch(payload)

    def distribute_execution(self, execution: Any) -> TradeCopierExecutionResult:
        try:
            if str(self._get(execution, "symbol", self._get(execution, "canonical_symbol", ""))).upper() != self.ALLOWED_SYMBOL:
                return self.store.store_result(self._blocked_result(execution, ["Demo trade copier allows EURUSD only."]))
            if bool(self._get(execution, "live_execution_enabled", False)) or bool(self._get(execution, "broker_execution_enabled", False)):
                return self.store.store_result(self._blocked_result(execution, ["Live or broker execution flags are not allowed."]))
            if not bool(self._get(execution, "demo_execution", True)) or not bool(self._get(execution, "simulation_only", True)):
                return self.store.store_result(self._blocked_result(execution, ["Trade copier execution bridge requires demo simulation records."]))
            if float(self._get(execution, "lot", self._get(execution, "requested_lot", 0.0)) or 0.0) > 0.01:
                return self.store.store_result(self._blocked_result(execution, ["Per-account copy lot must be <= 0.01."]))

            batch = self.create_copy_batch_from_execution(execution)
            summary = self.trade_copier_service.synchronize_batch(batch.copy_batch_id)
            synchronized_batch = self.trade_copier_service.get_batch(batch.copy_batch_id) or batch
            result = TradeCopierExecutionResult(
                source_execution_id=str(self._get(execution, "final_execution_id", self._get(execution, "execution_id", "")) or ""),
                source_signal_id=str(self._get(execution, "decision_id", self._get(execution, "signal_id", "")) or ""),
                source_symbol=synchronized_batch.canonical_symbol,
                source_action=synchronized_batch.action,
                source_lot=float(self._get(execution, "lot", self._get(execution, "requested_lot", 0.0)) or 0.0),
                copy_batch_id=synchronized_batch.copy_batch_id,
                copied_accounts=[
                    item.account_id
                    for item in synchronized_batch.account_copy_results
                    if item.status in {"PLANNED", "COPIED"} and not item.rejection_reasons
                ],
                skipped_accounts=[
                    item.account_id
                    for item in synchronized_batch.account_copy_results
                    if item.status == "SKIPPED_DUPLICATE"
                ],
                failed_accounts=[
                    item.account_id
                    for item in synchronized_batch.account_copy_results
                    if item.status in {"REJECTED", "BLOCKED", "MT5_UNAVAILABLE", "FAILED_SAFE"}
                ],
                duplicate_blocked=bool(synchronized_batch.duplicate_blocked),
                copy_status=self._copy_status(synchronized_batch, summary),
                simulation_only=True,
                demo_execution=True,
                live_execution_enabled=False,
                broker_execution_enabled=False,
            )
            return self.store.store_result(result)
        except Exception:
            return self.store.store_result(self._blocked_result(execution, ["Trade copier execution bridge failed safe."]))

    def get_copy_status(self, copy_batch_id: str):
        return self.trade_copier_service.get_batch(copy_batch_id)

    def list_results(self, limit: int = 100):
        return self.store.list_results(limit)

    def get_result(self, copier_execution_id: str):
        return self.store.get_result(copier_execution_id)

    def _payload_from_execution(self, execution: Any) -> dict[str, Any]:
        return {
            "signal_id": str(self._get(execution, "decision_id", self._get(execution, "signal_id", "strategy-demo-copy"))),
            "symbol": str(self._get(execution, "symbol", self._get(execution, "canonical_symbol", ""))).upper(),
            "canonical_symbol": str(self._get(execution, "symbol", self._get(execution, "canonical_symbol", ""))).upper(),
            "action": str(self._get(execution, "action", "")).upper(),
            "total_lot": float(self._get(execution, "lot", self._get(execution, "requested_lot", 0.01)) or 0.01),
            "lot": float(self._get(execution, "lot", self._get(execution, "requested_lot", 0.01)) or 0.01),
            "order_type": "MARKET",
            "confirm_demo_execution": True,
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def _copy_status(self, batch: Any, summary: Any | None) -> CopyExecutionStatus:
        if batch.duplicate_blocked and not [
            item for item in batch.account_copy_results if item.status in {"PLANNED", "COPIED"}
        ]:
            return "DUPLICATE_BLOCKED"
        if summary is not None and getattr(summary, "partial_copy", False):
            return "PARTIAL_COPY"
        if any(item.status in {"REJECTED", "BLOCKED", "MT5_UNAVAILABLE", "FAILED_SAFE"} for item in batch.account_copy_results):
            if any(item.status in {"PLANNED", "COPIED"} for item in batch.account_copy_results):
                return "PARTIAL_COPY"
            return "FAILED_SAFE"
        return "COPIED"

    def _blocked_result(self, execution: Any, reasons: list[str]) -> TradeCopierExecutionResult:
        return TradeCopierExecutionResult(
            source_execution_id=str(self._get(execution, "final_execution_id", self._get(execution, "execution_id", "")) or ""),
            source_signal_id=str(self._get(execution, "decision_id", self._get(execution, "signal_id", "")) or ""),
            source_symbol=str(self._get(execution, "symbol", self._get(execution, "canonical_symbol", ""))).upper() or None,
            source_action=str(self._get(execution, "action", "")).upper() or None,
            source_lot=float(self._get(execution, "lot", self._get(execution, "requested_lot", 0.0)) or 0.0),
            failed_accounts=reasons,
            copy_status="FAILED_SAFE",
            simulation_only=True,
            demo_execution=True,
            live_execution_enabled=False,
            broker_execution_enabled=False,
        )

    def _get(self, obj: Any | None, key: str, default: Any) -> Any:
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)
