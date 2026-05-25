from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class PipelineStatus(BaseModel):
    """Runtime progress representation for one orchestration workflow."""

    symbol: str
    status: str
    current_step: str
    completed_steps: list[str] = Field(default_factory=list)
    failed_steps: list[str] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class OrchestrationDecision(BaseModel):
    """Final advisory gate outcome before any simulation may be attempted."""

    symbol: str
    approved: bool
    final_action: Literal["BUY", "SELL", "WAIT", "AVOID"]
    confidence: float = Field(ge=0, le=100)
    blocked_by: Literal["NEWS", "RISK", "AI", "STRATEGY", "EXECUTION_VALIDATION", "NONE"]
    reasons: list[str] = Field(default_factory=list)
    ai_decision: dict[str, Any] = Field(default_factory=dict)
    news_status: dict[str, Any] = Field(default_factory=dict)
    risk_status: dict[str, Any] = Field(default_factory=dict)
    strategy_snapshot: dict[str, Any] = Field(default_factory=dict)
    execution_mode: str = "SIMULATION_ONLY"
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PipelineResult(BaseModel):
    """Serializable outcome of one complete orchestration request."""

    success: bool
    symbol: str
    decision: OrchestrationDecision
    steps_run: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SymbolMonitorConfig(BaseModel):
    """In-memory monitoring configuration; no scheduler is active in Day 10."""

    symbols: list[str] = Field(default_factory=lambda: ["XAUUSD"])
    default_timeframe: str = "M15"
    enabled: bool = True
    simulation_only: bool = True
