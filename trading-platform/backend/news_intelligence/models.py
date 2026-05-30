from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


NewsImpact = Literal["LOW", "MEDIUM", "HIGH"]
NewsRiskLevel = Literal["LOW", "MEDIUM", "HIGH", "EXTREME"]


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
