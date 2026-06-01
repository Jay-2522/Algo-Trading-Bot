from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


FinalExecutionStatus = Literal[
    "DEMO_EXECUTION_SENT",
    "DEMO_FILLED",
    "DEMO_REJECTED",
    "MT5_UNAVAILABLE",
    "BLOCKED_NOT_CONFIRMED",
    "BLOCKED_CANDIDATE_NOT_FOUND",
    "BLOCKED_CANDIDATE_NOT_APPROVED",
    "BLOCKED_DUPLICATE_EXECUTION",
    "BLOCKED_STALE_CANDIDATE",
    "BLOCKED_RISK_ENGINE",
    "BLOCKED_DEMO_GUARD",
    "FAILED_SAFE",
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FinalDemoExecutionRequest(BaseModel):
    candidate_id: str
    confirm_demo_execution: bool = False
    requested_by: str | None = None
    reason: str = ""


class FinalDemoExecutionDecision(BaseModel):
    final_execution_id: str = Field(default_factory=lambda: f"final_demo_exec_{uuid4().hex[:12]}")
    candidate_id: str
    approval_id: str | None = None
    decision_id: str | None = None
    queue_preview_id: str | None = None
    symbol: str | None = None
    action: str | None = None
    lot: float = 0.0
    approved_for_execution: bool = False
    execution_status: FinalExecutionStatus = "FAILED_SAFE"
    rejection_reasons: list[str] = Field(default_factory=list)
    risk_decision_id: str | None = None
    demo_execution_result_id: str | None = None
    copier_execution_id: str | None = None
    copy_batch_id: str | None = None
    mt5_retcode: int | str | None = None
    mt5_order: int | str | None = None
    mt5_deal: int | str | None = None
    simulation_only: bool = True
    demo_execution: bool = True
    live_execution_enabled: bool = False
    broker_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)
