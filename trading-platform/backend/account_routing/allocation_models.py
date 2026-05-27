from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


AllocationMode = Literal["EQUAL", "FIXED_LOT", "RISK_WEIGHTED", "CONSERVATIVE", "DISABLED"]


class AccountRiskProfile(BaseModel):
    account_id: str
    broker_id: str
    account_mode: Literal["DEMO", "READ_ONLY", "LIVE_DISABLED"] = "DEMO"
    balance: float = 10000.0
    equity: float = 10000.0
    free_margin: float = 10000.0
    max_risk_percent: float = 1.0
    daily_loss_limit: float = 5.0
    max_lot_per_trade: float = 1.0
    max_symbol_exposure: float = 3.0
    enabled: bool = True
    demo_ready: bool = True
    read_only: bool = True
    simulation_only: bool = True
    live_execution_enabled: bool = False


class AccountBalanceSnapshot(BaseModel):
    account_id: str
    broker_id: str
    balance: float
    equity: float
    free_margin: float
    margin_level: float | None = None
    floating_pnl: float = 0.0
    healthy: bool = True
    warnings: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)


class LotAllocation(BaseModel):
    account_id: str
    broker_id: str
    canonical_symbol: str
    action: str
    allocation_mode: AllocationMode
    allocated_lot: float = 0.0
    risk_percent: float = 0.0
    risk_amount: float = 0.0
    exposure_percent: float = 0.0
    allocation_status: Literal["APPROVED", "REDUCED", "REJECTED", "BLOCKED"] = "REJECTED"
    rejection_reason: str | None = None
    simulation_only: bool = True
    live_execution_enabled: bool = False


class AllocationDecision(BaseModel):
    decision_id: str = Field(default_factory=lambda: f"alloc_{uuid4().hex[:12]}")
    signal_id: str
    canonical_symbol: str
    action: str
    allocation_mode: AllocationMode
    allocations: list[LotAllocation] = Field(default_factory=list)
    total_allocated_lot: float = 0.0
    total_risk_percent: float = 0.0
    exposure_summary: dict[str, float | int | str] = Field(default_factory=dict)
    routing_ready: bool = False
    warnings: list[str] = Field(default_factory=list)
    rejection_reasons: list[str] = Field(default_factory=list)
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)
