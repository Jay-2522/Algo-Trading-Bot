from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


ApprovalStatus = Literal[
    "APPROVED_FOR_DEMO_EXECUTION",
    "REJECTED_NOT_CONFIRMED",
    "REJECTED_NO_QUEUE_PREVIEW",
    "REJECTED_BRIDGE_NOT_APPROVED",
    "REJECTED_RISK_NOT_APPROVED",
    "REJECTED_STALE_PREVIEW",
    "REJECTED_DUPLICATE_APPROVAL",
    "FAILED_SAFE",
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def default_expiry() -> datetime:
    return utc_now() + timedelta(minutes=15)


class DemoExecutionApprovalRequest(BaseModel):
    decision_id: str
    confirm_demo_approval: bool = False
    requested_by: str | None = None
    reason: str = ""


class DemoExecutionCandidate(BaseModel):
    candidate_id: str = Field(default_factory=lambda: f"demo_candidate_{uuid4().hex[:12]}")
    approval_id: str
    decision_id: str
    queue_preview_id: str
    symbol: str
    action: str
    lot: float = 0.01
    allocation_mode: str = "EQUAL"
    strategy_name: str = "UNKNOWN_STRATEGY"
    ready_for_demo_execution: bool = True
    requires_final_execution_confirmation: bool = True
    simulation_only: bool = True
    demo_execution: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)


class DemoExecutionApprovalDecision(BaseModel):
    approval_id: str = Field(default_factory=lambda: f"demo_approval_{uuid4().hex[:12]}")
    decision_id: str
    signal_id: str | None = None
    symbol: str | None = None
    action: str | None = None
    queue_preview_id: str | None = None
    approved: bool = False
    approval_status: ApprovalStatus = "FAILED_SAFE"
    rejection_reasons: list[str] = Field(default_factory=list)
    demo_execution_candidate_id: str | None = None
    expires_at: datetime = Field(default_factory=default_expiry)
    simulation_only: bool = True
    demo_execution: bool = True
    live_execution_enabled: bool = False
    broker_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)
