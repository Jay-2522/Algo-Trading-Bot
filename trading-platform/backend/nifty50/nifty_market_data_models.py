from datetime import datetime, timezone

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class NIFTYCandle(BaseModel):
    symbol: str = "NIFTY50"
    timeframe: str = "M15"
    timestamp: datetime = Field(default_factory=utc_now)
    open: float
    high: float
    low: float
    close: float
    volume: int = 0
    placeholder: bool = False


class NIFTYTick(BaseModel):
    symbol: str = "NIFTY50"
    price: float
    timestamp: datetime = Field(default_factory=utc_now)
    placeholder: bool = False


class NIFTYMarketDataHealth(BaseModel):
    candles_available: int = 0
    ticks_available: int = 0
    valid_candles: int = 0
    invalid_candles: int = 0
    supported_timeframes: list[str] = Field(default_factory=lambda: ["M1", "M5", "M15", "H1", "H4", "D1"])
    data_source: str = "MANUAL_INGESTION"
    placeholder: bool = True
    timestamp: datetime = Field(default_factory=utc_now)
