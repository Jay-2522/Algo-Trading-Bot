from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, model_validator


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


class LoopConfig(BaseModel):
    """Runtime controls for the rate-limited simulation-only scheduler."""

    enabled: bool = False
    simulation_only: bool = True
    live_execution_enabled: bool = False
    interval_seconds: int = Field(default=10, ge=5)
    max_symbols_per_cycle: int = Field(default=5, ge=1, le=100)
    monitored_symbols: list[str] = Field(default_factory=lambda: ["XAUUSD"])

    @model_validator(mode="after")
    def enforce_simulation_boundary(self) -> "LoopConfig":
        if not self.simulation_only or self.live_execution_enabled:
            raise ValueError("Background trading loop supports simulation-only operation.")
        normalized = []
        for symbol in self.monitored_symbols:
            value = symbol.strip().upper()
            if value and value not in normalized:
                normalized.append(value)
        if not normalized:
            raise ValueError("At least one monitored symbol is required.")
        self.monitored_symbols = normalized
        return self


class LoopRunResult(BaseModel):
    """Outcome of one symbol evaluation performed by the loop."""

    symbol: str
    success: bool
    decision: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    timestamp: str = Field(default_factory=utc_timestamp)


class LoopStatus(BaseModel):
    """Observable lifecycle and result state for the controlled scheduler."""

    status: str
    running: bool
    paused: bool
    simulation_only: bool
    live_execution_enabled: bool
    monitored_symbols: list[str] = Field(default_factory=list)
    interval_seconds: int
    total_runs: int
    failed_runs: int
    last_run_at: str | None = None
    last_decision: dict[str, Any] | None = None
    timestamp: str = Field(default_factory=utc_timestamp)


class LoopControlResponse(BaseModel):
    """Lifecycle operation response including the resulting state snapshot."""

    success: bool
    action: str
    message: str
    status: LoopStatus
    timestamp: str = Field(default_factory=utc_timestamp)
