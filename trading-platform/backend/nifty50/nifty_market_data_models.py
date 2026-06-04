from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class NIFTYCandle(BaseModel):
    symbol: str
    timeframe: str
    timestamp: datetime = Field(default_factory=utc_now)
    open: float
    high: float
    low: float
    close: float
    volume: int = 0
    placeholder: bool = False

    @field_validator("symbol", "timeframe")
    @classmethod
    def require_non_empty_text(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Field must be provided.")
        return value.strip().upper()


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
