from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PortfolioAccountSummary(BaseModel):
    account_id: str
    broker_id: str
    account_mode: str
    balance: float
    equity: float
    free_margin: float
    enabled: bool
    demo_ready: bool
    supported_symbols: list[str] = Field(default_factory=list)
    risk_status: str
    simulation_only: bool = True
    live_execution_enabled: bool = False


class PortfolioExposureSummary(BaseModel):
    total_accounts: int
    enabled_accounts: int
    supported_symbols: list[str] = Field(default_factory=list)
    blocked_symbols: list[str] = Field(default_factory=list)
    total_simulated_balance: float
    total_simulated_equity: float
    exposure_by_symbol: dict[str, Any] = Field(default_factory=dict)
    risk_summary: dict[str, Any] = Field(default_factory=dict)
    simulation_only: bool = True
    live_execution_enabled: bool = False


class PortfolioOverview(BaseModel):
    portfolio_status: str
    accounts: list[PortfolioAccountSummary] = Field(default_factory=list)
    exposure_summary: PortfolioExposureSummary
    pnl_summary: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)
