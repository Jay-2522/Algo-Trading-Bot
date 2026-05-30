from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


NewsImpact = Literal["LOW", "MEDIUM", "HIGH"]
NewsRiskLevel = Literal["LOW", "MEDIUM", "HIGH", "EXTREME"]
NewsTradeAction = Literal["ALLOW", "REDUCE_RISK", "BLOCK", "WAIT_FOR_STABILIZATION"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class NewsEvent(BaseModel):
    event_id: str
    title: str
    category: str
    currency: str
    impact: NewsImpact
    scheduled_time: datetime
    source: str
    risk_level: NewsRiskLevel
    active: bool = False
    warnings: list[str] = Field(default_factory=list)


class NewsIntelligenceStatus(BaseModel):
    status: str
    architecture_ready: bool
    sources_supported: list[str] = Field(default_factory=list)
    event_types_supported: list[str] = Field(default_factory=list)
    risk_engine_ready: bool
    strategy_integration_ready: bool
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)


class EconomicCalendarEvent(BaseModel):
    event_id: str
    source: str
    title: str
    currency: str
    impact: NewsImpact
    category: str
    scheduled_time: datetime | None = None
    actual: str | None = None
    forecast: str | None = None
    previous: str | None = None
    risk_level: NewsRiskLevel
    pre_event_window_minutes: int = 0
    post_event_window_minutes: int = 0
    active_risk_window: bool = False
    trade_action: NewsTradeAction = "ALLOW"
    warnings: list[str] = Field(default_factory=list)


class NewsRiskContext(BaseModel):
    high_impact_event_active: bool = False
    active_events: list[EconomicCalendarEvent] = Field(default_factory=list)
    upcoming_events: list[EconomicCalendarEvent] = Field(default_factory=list)
    risk_level: NewsRiskLevel = "LOW"
    trade_action: NewsTradeAction = "ALLOW"
    reason: str = "No active news risk window."
    sources_checked: list[str] = Field(default_factory=list)
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)
