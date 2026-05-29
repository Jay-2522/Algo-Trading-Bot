from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AccountDemoExecutionPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: f"acct_demo_plan_{uuid4().hex[:12]}")
    signal_id: str
    account_id: str
    broker_id: str
    canonical_symbol: str
    broker_symbol: str
    action: str
    lot: float
    order_type: str = "MARKET"
    eligible: bool = False
    rejection_reasons: list[str] = Field(default_factory=list)
    simulation_only: bool = True
    demo_execution: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)


class AccountExecutionResult(BaseModel):
    account_id: str
    broker_id: str
    status: Literal["DEMO_FILLED", "DEMO_REJECTED", "BLOCKED", "SKIPPED_DUPLICATE", "MT5_UNAVAILABLE", "FAILED_SAFE"]
    mt5_retcode: int | str | None = None
    mt5_order: int | str | None = None
    mt5_deal: int | str | None = None
    rejection_reasons: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)


class MultiAccountDemoExecutionResult(BaseModel):
    batch_id: str = Field(default_factory=lambda: f"multi_demo_batch_{uuid4().hex[:12]}")
    signal_id: str
    canonical_symbol: str
    action: str
    total_targets: int = 0
    attempted: int = 0
    filled: int = 0
    rejected: int = 0
    blocked: int = 0
    account_results: list[AccountExecutionResult] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    simulation_only: bool = True
    demo_execution: bool = True
    live_execution_enabled: bool = False
    broker_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)
