from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


ManagementState = Literal[
    "PENDING",
    "ACTIVE",
    "PARTIAL_TP_1",
    "PARTIAL_TP_2",
    "BREAK_EVEN",
    "TRAILING",
    "CLOSING",
    "CLOSED",
    "INVALIDATED",
    "EMERGENCY_EXIT",
]


class PositionState(BaseModel):
    position_id: str
    state: ManagementState
    previous_state: ManagementState | None = None
    reason: str = ""
    timestamp: datetime = Field(default_factory=utc_now)


class ManagedPosition(BaseModel):
    management_id: str = Field(default_factory=lambda: f"PMG-{uuid4().hex}")
    position_id: str
    candidate_id: str
    symbol: str
    timeframe: str
    direction: Literal["BUY", "SELL"]
    state: ManagementState = "ACTIVE"
    entry_price: float
    initial_stop: float
    current_stop: float
    target_level: float
    initial_risk: float = Field(gt=0.0)
    original_size: float = Field(default=1.0, gt=0.0)
    remaining_size: float = Field(default=1.0, ge=0.0)
    realized_rr: float = 0.0
    tp1_achieved: bool = False
    tp2_achieved: bool = False
    break_even_applied: bool = False
    trailing_active: bool = False
    opened_at: datetime
    simulation_only: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class PartialTakeProfit(BaseModel):
    position_id: str
    level: Literal["TP1", "TP2", "TP3"]
    trigger_price: float
    rr_level: float
    reduction_percent: float = Field(ge=0.0, le=100.0)
    remaining_size: float = Field(ge=0.0)
    realized_rr: float
    runner_preserved: bool = True
    reason: str
    timestamp: datetime = Field(default_factory=utc_now)


class BreakEvenAdjustment(BaseModel):
    position_id: str
    applied: bool = False
    previous_stop: float
    adjusted_stop: float
    protected_rr: float = 0.0
    reason: str
    timestamp: datetime = Field(default_factory=utc_now)


class TrailingStopAdjustment(BaseModel):
    position_id: str
    applied: bool = False
    previous_stop: float
    adjusted_stop: float
    reference_level: float | None = None
    method: str = "STRUCTURE_AWARE"
    reason: str
    timestamp: datetime = Field(default_factory=utc_now)


class StructuralExitSignal(BaseModel):
    position_id: str
    exit_required: bool = False
    exit_reason: str
    severity: Literal["INFO", "WARNING", "CRITICAL"] = "INFO"
    confidence: float = Field(default=0.0, ge=0.0, le=100.0)
    structural_evidence: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)


class EmergencyExitSignal(BaseModel):
    position_id: str | None = None
    triggered: bool = False
    trigger_source: str = "NONE"
    severity: Literal["INFO", "WARNING", "CRITICAL"] = "INFO"
    shutdown_reason: str = ""
    emergency_action: Literal["NONE", "CLOSE_SIMULATION_POSITION", "BLOCK_NEW_SIMULATIONS"] = "NONE"
    timestamp: datetime = Field(default_factory=utc_now)


class ManagementDecision(BaseModel):
    decision_id: str = Field(default_factory=lambda: f"PMD-{uuid4().hex}")
    position_id: str | None = None
    action: Literal[
        "NO_POSITION",
        "HOLD",
        "PARTIAL_TAKE_PROFIT",
        "MOVE_TO_BREAK_EVEN",
        "TRAIL_STOP",
        "EXIT_SIMULATION",
        "EMERGENCY_EXIT",
    ] = "HOLD"
    state: ManagementState | None = None
    reason: str
    confidence: float = Field(default=0.0, ge=0.0, le=100.0)
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)


class InstitutionalPositionManagement(BaseModel):
    symbol: str
    timeframe: str
    managed_positions: list[ManagedPosition] = Field(default_factory=list)
    active_positions: list[ManagedPosition] = Field(default_factory=list)
    decisions: list[ManagementDecision] = Field(default_factory=list)
    partial_take_profits: list[PartialTakeProfit] = Field(default_factory=list)
    break_even_adjustments: list[BreakEvenAdjustment] = Field(default_factory=list)
    trailing_stop_adjustments: list[TrailingStopAdjustment] = Field(default_factory=list)
    structural_exit_signals: list[StructuralExitSignal] = Field(default_factory=list)
    emergency_exit: EmergencyExitSignal | None = None
    session_exit_reasons: list[str] = Field(default_factory=list)
    latest_state: PositionState | None = None
    management_status: Literal["NO_POSITION", "ACTIVE", "MANAGING", "EXIT_REQUIRED", "EMERGENCY", "CLOSED"] = "NO_POSITION"
    summary: str = ""
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)
