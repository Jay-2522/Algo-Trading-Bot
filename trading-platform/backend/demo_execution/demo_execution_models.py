from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MT5DemoAccountStatus(BaseModel):
    terminal_available: bool = False
    account_connected: bool = False
    account_login: int | None = None
    broker_server: str | None = None
    account_trade_mode: str | int | None = None
    is_demo_account: bool = False
    demo_execution_allowed: bool = False
    rejection_reasons: list[str] = Field(default_factory=list)
    simulation_only: bool = True
    live_execution_enabled: bool = False
    broker_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)


class DemoExecutionRequest(BaseModel):
    queue_id: str
    confirm_demo_execution: bool = False
    requested_by: str = "unknown"
    reason: str = ""


class DemoExecutionResult(BaseModel):
    execution_id: str = Field(default_factory=lambda: f"demo_exec_{uuid4().hex[:12]}")
    queue_id: str
    broker_id: str | None = None
    account_id: str | None = None
    canonical_symbol: str | None = None
    broker_symbol: str | None = None
    action: str | None = None
    requested_lot: float = 0.0
    executed_lot: float = 0.0
    order_type: str = "MARKET"
    mt5_retcode: int | str | None = None
    mt5_order: int | str | None = None
    mt5_deal: int | str | None = None
    status: Literal["DEMO_FILLED", "DEMO_REJECTED", "BLOCKED", "FAILED_SAFE", "MT5_UNAVAILABLE"]
    rejection_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    demo_execution: bool = True
    simulation_only: bool = True
    live_execution_enabled: bool = False
    broker_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)
