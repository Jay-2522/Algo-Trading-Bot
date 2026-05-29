from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


CopyStatus = Literal["READY", "IN_PROGRESS", "COMPLETED", "PARTIAL", "REJECTED", "BLOCKED", "FAILED_SAFE"]
AccountCopyState = Literal["PLANNED", "COPIED", "REJECTED", "BLOCKED", "MT5_UNAVAILABLE", "SKIPPED_DUPLICATE", "FAILED_SAFE"]


class AccountCopyStatus(BaseModel):
    account_id: str
    broker_id: str
    status: AccountCopyState
    mt5_retcode: int | str | None = None
    mt5_order: int | str | None = None
    mt5_deal: int | str | None = None
    rejection_reasons: list[str] = Field(default_factory=list)
    copied: bool = False
    timestamp: datetime = Field(default_factory=utc_now)


class TradeCopyBatch(BaseModel):
    copy_batch_id: str = Field(default_factory=lambda: f"copy_batch_{uuid4().hex[:12]}")
    source_signal_id: str
    canonical_symbol: str
    action: str
    target_accounts: list[str] = Field(default_factory=list)
    copy_status: CopyStatus = "READY"
    account_copy_results: list[AccountCopyStatus] = Field(default_factory=list)
    partial_copy: bool = False
    duplicate_blocked: bool = False
    warnings: list[str] = Field(default_factory=list)
    demo_execution: bool = True
    simulation_only: bool = True
    live_execution_enabled: bool = False
    broker_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)


class CopySynchronizationSummary(BaseModel):
    copy_batch_id: str
    total_targets: int
    copied_count: int
    rejected_count: int
    blocked_count: int
    unavailable_count: int
    partial_copy: bool
    synchronization_status: CopyStatus
    warnings: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)
