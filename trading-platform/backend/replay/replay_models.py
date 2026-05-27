from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ReplayRequest(BaseModel):
    symbol: str = "XAUUSD"
    timeframe: Literal["M5", "M15", "H1", "H4"] = "M15"
    start_time: datetime | None = None
    end_time: datetime | None = None
    initial_balance: float = Field(default=10000.0, gt=0.0)
    window_size: int = Field(default=100, ge=10)
    step_size: int = Field(default=5, ge=1)
    max_steps: int | None = Field(default=50, ge=1)
    simulation_only: bool = True

    @model_validator(mode="after")
    def force_simulation_only(self):
        self.symbol = self.symbol.strip().upper()
        self.timeframe = self.timeframe.strip().upper()
        self.simulation_only = True
        return self


class ReplayStepResult(BaseModel):
    step_index: int = Field(ge=0)
    replay_time: datetime
    candles_visible: int = Field(ge=0)
    institutional_state: dict[str, Any] = Field(default_factory=dict)
    simulation_decision: dict[str, Any] = Field(default_factory=dict)
    paper_trade_state: dict[str, Any] = Field(default_factory=dict)
    position_state: dict[str, Any] = Field(default_factory=dict)
    event_type: Literal[
        "ANALYSIS_STEP",
        "SIMULATION_DECISION",
        "PAPER_TRADE_CREATED",
        "PAPER_TRADE_CLOSED",
        "BLOCKED",
        "ERROR_SAFE",
    ] = "ANALYSIS_STEP"
    confidence: float = Field(default=0.0, ge=0.0, le=100.0)
    notes: list[str] = Field(default_factory=list)


class ReplayRunResult(BaseModel):
    replay_id: str = Field(default_factory=lambda: f"RPL-{uuid4().hex}")
    symbol: str
    timeframe: str
    start_time: datetime | None = None
    end_time: datetime | None = None
    total_steps: int = Field(default=0, ge=0)
    decisions_count: int = Field(default=0, ge=0)
    simulated_trades_count: int = Field(default=0, ge=0)
    blocked_count: int = Field(default=0, ge=0)
    wait_count: int = Field(default=0, ge=0)
    avoid_count: int = Field(default=0, ge=0)
    win_count: int = Field(default=0, ge=0)
    loss_count: int = Field(default=0, ge=0)
    breakeven_count: int = Field(default=0, ge=0)
    net_rr: float = 0.0
    max_drawdown: float = 0.0
    summary: str = ""
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)
    step_results: list[ReplayStepResult] = Field(default_factory=list)


class ReplayStatus(BaseModel):
    status: Literal["operational", "degraded"] = "operational"
    mode: str = "HISTORICAL_INSTITUTIONAL_REPLAY"
    simulation_only: bool = True
    live_execution_enabled: bool = False
    supported_timeframes: list[str] = Field(default_factory=lambda: ["M5", "M15", "H1", "H4"])
