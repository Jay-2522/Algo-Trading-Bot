from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ReplayScenarioSummary(BaseModel):
    replay_id: str
    symbol: str
    timeframe: str
    total_steps: int = Field(default=0, ge=0)
    total_decisions: int = Field(default=0, ge=0)
    total_trades: int = Field(default=0, ge=0)
    win_rate: float = Field(default=0.0, ge=0.0, le=100.0)
    net_rr: float = 0.0
    block_rate: float = Field(default=0.0, ge=0.0, le=100.0)
    average_confidence: float = Field(default=0.0, ge=0.0, le=100.0)
    optimization_status: str = "INSUFFICIENT_DATA"
    score: float = Field(default=0.0, ge=0.0, le=100.0)
    rank: int = Field(default=0, ge=0)


class ReplayScenarioComparison(BaseModel):
    comparison_id: str = Field(default_factory=lambda: f"RCMP-{uuid4().hex}")
    scenario_count: int = Field(default=0, ge=0)
    scenarios: list[ReplayScenarioSummary] = Field(default_factory=list)
    best_scenario: ReplayScenarioSummary | None = None
    weakest_scenario: ReplayScenarioSummary | None = None
    common_weaknesses: list[str] = Field(default_factory=list)
    key_insights: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)


class ReplayTimeframeComparison(BaseModel):
    symbol: str
    timeframes_compared: list[str] = Field(default_factory=list)
    best_timeframe: str = "N/A"
    weakest_timeframe: str = "N/A"
    timeframe_summaries: dict[str, dict[str, Any]] = Field(default_factory=dict)
    insight: str = "Insufficient timeframe data for comparison."


class ReplayFilterComparison(BaseModel):
    filters_compared: list[str] = Field(default_factory=list)
    most_restrictive_filter: str = "NONE"
    least_restrictive_filter: str = "NONE"
    filter_block_rates: dict[str, float] = Field(default_factory=dict)
    insight: str = "Insufficient filter data for comparison."
