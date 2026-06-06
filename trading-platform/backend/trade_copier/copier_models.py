from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


CopierFoundationStatus = Literal[
    "MASTER_SIGNAL_CREATED",
    "QUEUED",
    "BLOCKED",
    "SKIPPED",
    "SIMULATION_ONLY",
    "FUTURE_EXECUTION_REQUIRED",
]


class MasterSignal(BaseModel):
    master_signal_id: str = Field(default_factory=lambda: f"master_signal_{uuid4().hex[:12]}")
    symbol: str
    side: str
    lot: float = 0.01
    source: str = "SIMULATION"
    status: CopierFoundationStatus = "MASTER_SIGNAL_CREATED"
    created_at: datetime = Field(default_factory=utc_now)
    simulation_only: bool = True
    live_execution_enabled: bool = False
    broker_execution_enabled: bool = False


class CopierAccount(BaseModel):
    account_id: str
    label: str
    environment: str = "DEMO"
    enabled_for_future_execution: bool = False
    status: CopierFoundationStatus = "SIMULATION_ONLY"
    simulation_only: bool = True
    live_execution_enabled: bool = False
    broker_execution_enabled: bool = False


class CopierQueueItem(BaseModel):
    queue_item_id: str = Field(default_factory=lambda: f"copier_queue_{uuid4().hex[:12]}")
    master_signal_id: str
    account_id: str
    symbol: str
    side: str
    lot: float
    status: CopierFoundationStatus = "SIMULATION_ONLY"
    reason: str = "Trade copier is architecture-ready but execution-disabled."
    created_at: datetime = Field(default_factory=utc_now)
    simulation_only: bool = True
    live_execution_enabled: bool = False
    broker_execution_enabled: bool = False


class CopierBatch(BaseModel):
    batch_id: str = Field(default_factory=lambda: f"copier_batch_{uuid4().hex[:12]}")
    master_signal_id: str
    status: CopierFoundationStatus = "SIMULATION_ONLY"
    queue_items: list[CopierQueueItem] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    simulation_only: bool = True
    live_execution_enabled: bool = False
    broker_execution_enabled: bool = False
