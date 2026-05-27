from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CanonicalMarketTick(BaseModel):
    canonical_symbol: str
    broker_id: str
    broker_symbol: str | None = None
    bid: float | None = None
    ask: float | None = None
    mid: float | None = None
    spread: float | None = None
    digits: int | None = None
    point: float | None = None
    market_type: str | None = None
    timestamp: datetime = Field(default_factory=utc_now)
    source: str
    usable: bool = False
    quality: Literal["GOOD", "WARNING", "INVALID", "UNAVAILABLE"] = "UNAVAILABLE"
    issues: list[str] = Field(default_factory=list)
    simulation_only: bool = True
    live_execution_enabled: bool = False


class CanonicalFeedReport(BaseModel):
    broker_id: str
    ticks: list[CanonicalMarketTick] = Field(default_factory=list)
    usable_symbols: list[str] = Field(default_factory=list)
    unusable_symbols: list[str] = Field(default_factory=list)
    overall_quality: Literal["GOOD", "WARNING", "INVALID", "UNAVAILABLE"]
    ai_ready: bool = False
    safety_status: str = "READ_ONLY_CANONICAL_FEED_LIVE_EXECUTION_DISABLED"
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)
