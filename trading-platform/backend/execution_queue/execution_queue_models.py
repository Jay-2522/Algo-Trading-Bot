from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ExecutionIntent(BaseModel):
    intent_id: str = Field(default_factory=lambda: f"exec_intent_{uuid4().hex[:12]}")
    signal_id: str
    account_id: str
    broker_id: str
    canonical_symbol: str
    broker_symbol: str | None = None
    action: Literal["BUY", "SELL", "CLOSE"]
    allocated_lot: float
    order_type: Literal["MARKET", "LIMIT", "STOP", "NONE"] = "MARKET"
    requested_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    source: str = "ALLOCATION_PREVIEW"
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)


class ExecutionQueueItem(BaseModel):
    queue_id: str = Field(default_factory=lambda: f"exec_queue_{uuid4().hex[:12]}")
    intent: ExecutionIntent
    status: Literal["QUEUED", "HELD", "CANCELLED", "FAILED_SAFE", "EXECUTION_DISABLED"] = "HELD"
    readiness: Literal["READY_FOR_DEMO_QUEUE", "WAITING_FOR_CONFIRMATION", "BLOCKED", "INVALID"] = "INVALID"
    validation_errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    simulation_only: bool = True
    live_execution_enabled: bool = False


class ExecutionQueueStatus(BaseModel):
    total_items: int = 0
    queued: int = 0
    held: int = 0
    cancelled: int = 0
    failed_safe: int = 0
    execution_disabled: int = 0
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)
