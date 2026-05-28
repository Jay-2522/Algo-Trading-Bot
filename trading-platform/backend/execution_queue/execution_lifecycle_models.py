from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SimulatedExecutionResult(BaseModel):
    execution_id: str = Field(default_factory=lambda: f"sim_exec_{uuid4().hex[:12]}")
    queue_id: str
    account_id: str
    broker_id: str
    canonical_symbol: str
    action: str
    requested_lot: float
    filled_lot: float = 0.0
    requested_price: float | None = None
    simulated_fill_price: float | None = None
    status: Literal["SIMULATED_FILLED", "SIMULATED_REJECTED", "SIMULATED_CANCELLED", "SIMULATION_BLOCKED"]
    rejection_reason: str | None = None
    slippage_points: float = 0.0
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)


class OrderLifecycleState(BaseModel):
    queue_id: str
    execution_id: str | None = None
    current_state: Literal[
        "CREATED",
        "VALIDATED",
        "SIMULATED_ACCEPTED",
        "SIMULATED_FILLED",
        "SIMULATED_REJECTED",
        "CANCELLED",
        "FAILED_SAFE",
    ] = "CREATED"
    history: list[dict[str, Any]] = Field(default_factory=list)
    opened_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    simulation_only: bool = True
    live_execution_enabled: bool = False


class ExecutionAuditEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"exec_audit_{uuid4().hex[:12]}")
    queue_id: str
    event_type: str
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=utc_now)
