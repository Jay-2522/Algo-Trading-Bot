from datetime import datetime, timedelta, timezone
from typing import Literal

from pydantic import BaseModel, Field, model_validator


SupportedBacktestTimeframe = Literal["M1", "M5", "M15", "H1", "H4"]


class HistoricalCandle(BaseModel):
    """Normalized historical OHLCV candle used only for deterministic replay."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int = Field(ge=0)


class BacktestRequest(BaseModel):
    """Configuration for one offline replay request."""

    symbol: str = "XAUUSD"
    timeframe: SupportedBacktestTimeframe = "M15"
    start_date: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc) - timedelta(days=14)
    )
    end_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    initial_balance: float = Field(default=10000.0, gt=0)
    lot_size: float = Field(default=0.01, gt=0, le=100)
    risk_reward: float = Field(default=2.0, ge=1.0, le=10.0)
    spread_points: float = Field(default=2.0, ge=0)
    slippage_points: float = Field(default=1.0, ge=0)
    max_candles: int = Field(default=600, ge=50, le=5000)

    @model_validator(mode="after")
    def validate_range(self) -> "BacktestRequest":
        self.symbol = self.symbol.strip().upper()
        if not self.symbol:
            raise ValueError("Symbol cannot be empty.")
        if self.end_date <= self.start_date:
            raise ValueError("End date must be later than start date.")
        return self


class TradeResult(BaseModel):
    """Closed simulated historical trade; this is not a broker execution record."""

    trade_id: str
    symbol: str
    side: Literal["BUY", "SELL"]
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    stop_loss: float
    take_profit: float
    lot_size: float
    pnl: float
    pnl_percent: float
    risk_reward: float
    outcome: Literal["WIN", "LOSS", "BREAKEVEN"]
    exit_reason: str
    spread_points: float
    slippage_points: float
    bars_held: int
    execution_mode: str = "SIMULATION_ONLY"


class EquityPoint(BaseModel):
    """Balance value following a simulated trade event."""

    timestamp: datetime
    balance: float
    drawdown_percent: float = Field(ge=0)
    trade_id: str | None = None


class PerformanceMetrics(BaseModel):
    """Risk and return measurements derived from a completed replay."""

    initial_balance: float
    ending_balance: float
    net_profit: float
    profit_percent: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    average_rr: float
    profit_factor: float
    expectancy: float
    sharpe_ratio: float
    equity_growth: float
    max_consecutive_wins: int
    max_consecutive_losses: int
    best_trade: float
    worst_trade: float


class BacktestResult(BaseModel):
    """Stored report for one completed offline simulation."""

    backtest_id: str
    symbol: str
    timeframe: SupportedBacktestTimeframe
    start_date: datetime
    end_date: datetime
    initial_balance: float
    ending_balance: float
    net_profit: float
    profit_percent: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    average_rr: float
    profit_factor: float
    sharpe_ratio: float
    equity_curve: list[EquityPoint] = Field(default_factory=list)
    trade_history: list[TradeResult] = Field(default_factory=list)
    metrics: PerformanceMetrics
    approved: bool
    status: str
    execution_mode: str = "SIMULATION_ONLY"
    errors: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
