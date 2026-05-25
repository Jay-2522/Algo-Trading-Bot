from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class JournalEntry(BaseModel):
    """Analytics-only record of a simulated trade outcome."""

    journal_id: str = Field(default_factory=lambda: f"JRN-{uuid4().hex}")
    symbol: str = Field(default="XAUUSD", min_length=1)
    side: Literal["BUY", "SELL"] = "BUY"
    timeframe: str = Field(default="M15", min_length=1)
    entry_price: float = Field(default=0.0, ge=0)
    stop_loss: float | None = Field(default=None, ge=0)
    take_profit: float | None = Field(default=None, ge=0)
    exit_price: float | None = Field(default=None, ge=0)
    pnl: float = 0.0
    rr: float = 0.0
    outcome: Literal["WIN", "LOSS", "BREAKEVEN", "OPEN"] = "OPEN"
    strategy_name: str = Field(default="UNSPECIFIED", min_length=1)
    session_name: str = Field(default="UNSPECIFIED", min_length=1)
    execution_quality: float = Field(default=100.0, ge=0, le=100)
    notes: str = ""
    simulated: bool = True
    timestamp: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def enforce_simulation_only(self) -> "JournalEntry":
        if not self.simulated:
            raise ValueError("Trade journal accepts simulation-only entries.")
        self.symbol = self.symbol.strip().upper()
        self.timeframe = self.timeframe.strip().upper()
        self.strategy_name = self.strategy_name.strip() or "UNSPECIFIED"
        self.session_name = self.session_name.strip().upper() or "UNSPECIFIED"
        return self


class RiskAnalytics(BaseModel):
    daily_drawdown_percent: float = 0.0
    current_exposure_percent: float = 0.0
    consecutive_losses: int = 0
    max_consecutive_losses: int = 0
    active_risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "LOW"
    risk_alerts: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)


class SessionPerformance(BaseModel):
    session_name: str
    total_trades: int = 0
    win_rate: float = 0.0
    net_profit: float = 0.0
    average_rr: float = 0.0
    best_trade: float = 0.0
    worst_trade: float = 0.0


class SymbolPerformance(BaseModel):
    symbol: str
    total_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    average_rr: float = 0.0
    net_profit: float = 0.0


class ExposureStatus(BaseModel):
    total_exposure_percent: float = 0.0
    symbols_exposed: list[str] = Field(default_factory=list)
    highest_risk_symbol: str | None = None
    exposure_warning: str | None = None


class RiskAlert(BaseModel):
    alert_id: str = Field(default_factory=lambda: f"ALT-{uuid4().hex}")
    severity: Literal["INFO", "WARNING", "CRITICAL"]
    category: str
    message: str
    timestamp: datetime = Field(default_factory=utc_now)
