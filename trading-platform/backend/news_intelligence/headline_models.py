from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from backend.news_intelligence.models import utc_now


HeadlineImpact = Literal["LOW", "MEDIUM", "HIGH", "EXTREME"]
HeadlineSentiment = Literal["BULLISH_GOLD", "BEARISH_GOLD", "MIXED", "NEUTRAL", "UNKNOWN"]
HeadlineRiskLevel = Literal["LOW", "MEDIUM", "HIGH", "EXTREME"]
HeadlineTradeAction = Literal["ALLOW", "REDUCE_RISK", "BLOCK", "WAIT_FOR_CONFIRMATION"]


class HeadlineEvent(BaseModel):
    headline_id: str = Field(default_factory=lambda: f"headline-{uuid4().hex}")
    source: str = "FINANCIAL_JUICE"
    title: str
    body: str = ""
    timestamp: datetime = Field(default_factory=utc_now)
    symbols: list[str] = Field(default_factory=list)
    currencies: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    impact: HeadlineImpact = "LOW"
    sentiment: HeadlineSentiment = "UNKNOWN"
    risk_level: HeadlineRiskLevel = "LOW"
    gold_relevance: bool = False
    usd_relevance: bool = False
    active: bool = True
    warnings: list[str] = Field(default_factory=list)


class HeadlineRiskContext(BaseModel):
    active_headlines: list[HeadlineEvent] = Field(default_factory=list)
    recent_headlines: list[HeadlineEvent] = Field(default_factory=list)
    highest_risk_level: HeadlineRiskLevel = "LOW"
    gold_sentiment: HeadlineSentiment = "UNKNOWN"
    usd_sentiment: str = "UNKNOWN"
    headline_trade_action: HeadlineTradeAction = "ALLOW"
    confidence_adjustment: float = 0.0
    reason: str = "No relevant headline risk."
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)


class HeadlineFilterDecision(BaseModel):
    decision_id: str = Field(default_factory=lambda: f"headline-filter-{uuid4().hex}")
    symbol: str = "XAUUSD"
    blocked: bool = False
    action_override: str | None = None
    confidence_cap: float | None = None
    confidence_penalty: float = 0.0
    confidence_adjustment: float = 0.0
    risk_level: HeadlineRiskLevel = "LOW"
    trade_action: HeadlineTradeAction = "ALLOW"
    gold_sentiment: HeadlineSentiment = "UNKNOWN"
    reason: str = "No relevant headline risk."
    client_message: str = "No relevant headline risk is active."
    technical_message: str = "Headline filter ALLOW: no real-time headline risk."
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)
