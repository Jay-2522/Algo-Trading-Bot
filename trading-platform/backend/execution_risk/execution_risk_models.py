from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ExecutionRiskPolicy(BaseModel):
    allowed_symbols: list[str] = Field(default_factory=lambda: ["EURUSD"])
    blocked_symbols: list[str] = Field(default_factory=lambda: ["XAUUSD", "NIFTY50"])
    max_lot_per_account: float = 0.01
    max_target_accounts: int = 3
    max_daily_demo_attempts: int = 20
    require_demo_account: bool = True
    require_confirmation: bool = True
    live_execution_enabled: bool = False
    broker_execution_enabled: bool = False
    simulation_only: bool = True
    demo_execution: bool = True


class ExecutionRiskDecision(BaseModel):
    decision_id: str = Field(default_factory=lambda: f"risk_decision_{uuid4().hex[:12]}")
    request_id: str
    canonical_symbol: str | None = None
    action: str | None = None
    account_id: str | None = None
    broker_id: str | None = None
    lot: float = 0.0
    approved: bool = False
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "BLOCKED"] = "BLOCKED"
    rejection_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    simulation_only: bool = True
    demo_execution: bool = True
    live_execution_enabled: bool = False
    broker_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)


class ExecutionRiskAuditEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"risk_audit_{uuid4().hex[:12]}")
    decision_id: str | None = None
    event_type: str
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    simulation_only: bool = True
    demo_execution: bool = True
    live_execution_enabled: bool = False
    broker_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)
