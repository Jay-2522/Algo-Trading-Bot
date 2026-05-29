from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


ReconciliationStatus = Literal["CONFIRMED", "PENDING", "REJECTED", "MISSING_POSITION", "MISMATCHED", "FAILED_SAFE"]


class ExecutionConfirmation(BaseModel):
    execution_id: str
    signal_id: str | None = None
    account_id: str | None = None
    broker_id: str | None = None
    canonical_symbol: str | None = None
    action: str | None = None
    mt5_order: int | str | None = None
    mt5_deal: int | str | None = None
    mt5_retcode: int | str | None = None
    order_confirmed: bool = False
    deal_confirmed: bool = False
    position_detected: bool = False
    reconciliation_status: ReconciliationStatus = "PENDING"
    warnings: list[str] = Field(default_factory=list)
    simulation_only: bool = True
    demo_execution: bool = True
    live_execution_enabled: bool = False
    broker_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)


class ReconciliationSummary(BaseModel):
    reconciliation_id: str = Field(default_factory=lambda: f"reconcile_{uuid4().hex[:12]}")
    total_executions: int
    confirmed: int
    pending: int
    rejected: int
    missing_position: int
    mismatched: int
    warnings: list[str] = Field(default_factory=list)
    simulation_only: bool = True
    demo_execution: bool = True
    live_execution_enabled: bool = False
    broker_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)


class ConfirmationAuditEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"confirm_audit_{uuid4().hex[:12]}")
    event_type: Literal[
        "CONFIRMATION_CREATED",
        "CONFIRMATION_CONFIRMED",
        "CONFIRMATION_REJECTED",
        "POSITION_RECONCILED",
        "POSITION_MISSING",
        "RECONCILIATION_MISMATCH",
    ]
    execution_id: str | None = None
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    simulation_only: bool = True
    demo_execution: bool = True
    live_execution_enabled: bool = False
    broker_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)
