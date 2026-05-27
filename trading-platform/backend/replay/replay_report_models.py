from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ReplayTradeAnalytics(BaseModel):
    total_trades: int = Field(default=0, ge=0)
    wins: int = Field(default=0, ge=0)
    losses: int = Field(default=0, ge=0)
    breakeven: int = Field(default=0, ge=0)
    win_rate: float = Field(default=0.0, ge=0.0, le=100.0)
    loss_rate: float = Field(default=0.0, ge=0.0, le=100.0)
    average_rr: float = 0.0
    net_rr: float = 0.0
    best_trade_rr: float = 0.0
    worst_trade_rr: float = 0.0
    average_holding_steps: float = Field(default=0.0, ge=0.0)
    expectancy: float = 0.0


class ReplayDecisionAnalytics(BaseModel):
    total_decisions: int = Field(default=0, ge=0)
    simulate_buy: int = Field(default=0, ge=0)
    simulate_sell: int = Field(default=0, ge=0)
    wait: int = Field(default=0, ge=0)
    avoid: int = Field(default=0, ge=0)
    no_trade: int = Field(default=0, ge=0)
    block_rate: float = Field(default=0.0, ge=0.0, le=100.0)
    average_confidence: float = Field(default=0.0, ge=0.0, le=100.0)
    most_common_action: str = "NO_TRADE"


class ReplayEquityPoint(BaseModel):
    step_index: int = Field(ge=0)
    replay_time: datetime | None = None
    balance: float
    equity: float
    drawdown: float = Field(default=0.0, ge=0.0)
    cumulative_rr: float = 0.0


class ReplayWeaknessInsight(BaseModel):
    insight_id: str
    category: Literal["CONFLUENCE", "SESSION", "RISK", "ENTRY_MODEL", "POSITION_MANAGEMENT", "DATA"]
    severity: Literal["INFO", "WARNING", "CRITICAL"]
    message: str
    suggested_action: str


class ReplayHistoricalReport(BaseModel):
    replay_id: str
    symbol: str
    timeframe: str
    trade_analytics: ReplayTradeAnalytics
    decision_analytics: ReplayDecisionAnalytics
    equity_curve: list[ReplayEquityPoint] = Field(default_factory=list)
    weakness_insights: list[ReplayWeaknessInsight] = Field(default_factory=list)
    best_conditions: list[str] = Field(default_factory=list)
    worst_conditions: list[str] = Field(default_factory=list)
    summary: str
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)
