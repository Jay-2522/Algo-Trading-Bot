from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from backend.news_intelligence.models import EconomicCalendarEvent, NewsRiskLevel, NewsTradeAction, utc_now


class NewsFilterDecision(BaseModel):
    decision_id: str = Field(default_factory=lambda: f"news-filter-{uuid4().hex}")
    symbol: str
    blocked: bool = False
    confidence_cap: float | None = None
    confidence_penalty: float = 0.0
    risk_level: NewsRiskLevel = "LOW"
    trade_action: NewsTradeAction = "ALLOW"
    active_events: list[EconomicCalendarEvent] = Field(default_factory=list)
    upcoming_events: list[EconomicCalendarEvent] = Field(default_factory=list)
    reason: str = "No relevant news risk."
    client_message: str = "No relevant news risk is active."
    technical_message: str = "News filter ALLOW: no relevant event window."
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)
