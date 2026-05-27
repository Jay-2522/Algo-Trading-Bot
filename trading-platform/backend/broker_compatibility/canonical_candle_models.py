from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CanonicalCandle(BaseModel):
    canonical_symbol: str
    broker_id: str
    timeframe: str
    timestamp: datetime = Field(default_factory=utc_now)
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: float | None = None
    source: Literal["MT5_READ_ONLY", "SIMULATION_FALLBACK"] = "SIMULATION_FALLBACK"
    usable: bool = False
    quality: Literal["GOOD", "WARNING", "INVALID", "UNAVAILABLE"] = "UNAVAILABLE"
    issues: list[str] = Field(default_factory=list)
    simulation_only: bool = True
    live_execution_enabled: bool = False


class MultiTimeframeFeedReport(BaseModel):
    broker_id: str
    canonical_symbol: str
    timeframes: list[str] = Field(default_factory=list)
    candles: dict[str, list[CanonicalCandle]] = Field(default_factory=dict)
    usable_timeframes: list[str] = Field(default_factory=list)
    unusable_timeframes: list[str] = Field(default_factory=list)
    overall_quality: Literal["GOOD", "WARNING", "INVALID", "UNAVAILABLE"] = "UNAVAILABLE"
    ai_ready: bool = False
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)
