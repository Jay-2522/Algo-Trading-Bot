from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


ReadinessStatus = Literal["FOUNDATION_READY", "STRATEGY_FOUNDATION_READY", "PENDING_BROKER_SELECTION", "BLOCKED", "READY_FOR_STRATEGY_LAYER"]


class NIFTY50Instrument(BaseModel):
    symbol: str = "NIFTY50"
    exchange: str = "NSE"
    instrument_type: str = "INDEX"
    lot_size: int = 1
    tick_size: float = 0.05
    currency: str = "INR"
    trading_session: str = "NSE_EQUITY"
    status: str = "STRATEGY_FOUNDATION_READY"
    warnings: list[str] = Field(default_factory=lambda: ["Live market data is not connected.", "NIFTY50 execution layer is pending."])


class IndianBrokerCandidate(BaseModel):
    broker_id: str
    broker_name: str
    api_supported: bool
    market_data_supported: bool
    order_execution_supported: bool
    paper_trading_supported: bool
    recommended: bool = False
    warnings: list[str] = Field(default_factory=list)


class NIFTY50MarketDataSnapshot(BaseModel):
    symbol: str = "NIFTY50"
    last_price: float | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    previous_close: float | None = None
    volume: int | None = None
    market_open: bool = False
    session_name: str = "UNKNOWN"
    data_source: str = "PLACEHOLDER"
    placeholder: bool = True
    timestamp: datetime = Field(default_factory=utc_now)


class NIFTY50ReadinessStatus(BaseModel):
    status: ReadinessStatus = "PENDING_BROKER_SELECTION"
    broker_architecture_ready: bool = True
    market_data_ready: bool = False
    strategy_ready: bool = False
    execution_ready: bool = False
    analytics_ready: bool = True
    selected_broker: str | None = None
    recommended_broker: str = "Dhan or Angel One"
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    simulation_only: bool = True
    live_execution_enabled: bool = False
    broker_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)

    def model_post_init(self, __context: Any) -> None:
        self.simulation_only = True
        self.live_execution_enabled = False
        self.broker_execution_enabled = False
