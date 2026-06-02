from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ClientAnalyticsOverview(BaseModel):
    status: str = "OPERATIONAL"
    total_signals: int = 0
    total_demo_executions: int = 0
    total_copy_batches: int = 0
    total_risk_blocks: int = 0
    total_news_blocks: int = 0
    active_symbols: list[str] = Field(default_factory=list)
    supported_symbols: list[str] = Field(default_factory=lambda: ["XAUUSD", "EURUSD", "NIFTY50"])
    best_symbol: str | None = None
    worst_symbol: str | None = None
    win_rate: float = 0.0
    net_pnl: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    simulation_only: bool = True
    demo_execution: bool = True
    live_execution_enabled: bool = False
    broker_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)

    def model_post_init(self, __context: Any) -> None:
        self.simulation_only = True
        self.demo_execution = True
        self.live_execution_enabled = False
        self.broker_execution_enabled = False


class SymbolPerformanceSummary(BaseModel):
    symbol: str
    total_signals: int = 0
    buy_signals: int = 0
    sell_signals: int = 0
    wait_signals: int = 0
    demo_executions: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    net_pnl: float = 0.0
    avg_confidence: float = 0.0
    best_trade: float = 0.0
    worst_trade: float = 0.0
    timestamp: datetime = Field(default_factory=utc_now)


class SessionPerformanceSummary(BaseModel):
    session: str
    total_signals: int = 0
    demo_executions: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    net_pnl: float = 0.0
    avg_confidence: float = 0.0
    timestamp: datetime = Field(default_factory=utc_now)


class RiskAnalyticsSummary(BaseModel):
    total_risk_checks: int = 0
    approved: int = 0
    blocked: int = 0
    news_blocks: int = 0
    regime_blocks: int = 0
    risk_engine_blocks: int = 0
    most_common_block_reason: str | None = None
    timestamp: datetime = Field(default_factory=utc_now)
