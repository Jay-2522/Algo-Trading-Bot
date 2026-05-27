from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class BrokerSymbolFeedQuality(BaseModel):
    broker_id: str
    canonical_symbol: str
    broker_symbol: str | None = None
    available: bool = False
    visible: bool | None = None
    bid: float | None = None
    ask: float | None = None
    spread: float | None = None
    spread_quality: Literal["EXCELLENT", "GOOD", "ACCEPTABLE", "WIDE", "INVALID"]
    tick_fresh: bool = False
    feed_quality: Literal["VALID", "WARNING", "INVALID", "UNAVAILABLE"]
    issues: list[str] = Field(default_factory=list)
    message: str
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)


class BrokerFeedQualityReport(BaseModel):
    broker_id: str
    symbol_qualities: list[BrokerSymbolFeedQuality] = Field(default_factory=list)
    valid_symbols: list[str] = Field(default_factory=list)
    warning_symbols: list[str] = Field(default_factory=list)
    invalid_symbols: list[str] = Field(default_factory=list)
    unavailable_symbols: list[str] = Field(default_factory=list)
    overall_quality: Literal["GOOD", "WARNING", "INVALID", "UNAVAILABLE"]
    ready_for_demo_observation: bool = False
    ready_for_demo_execution: bool = False
    safety_status: str = "READ_ONLY_FEED_VALIDATION_LIVE_EXECUTION_DISABLED"
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)
