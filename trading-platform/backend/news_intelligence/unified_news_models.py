from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from backend.news_intelligence.models import utc_now


UnifiedRiskLevel = Literal["LOW", "MEDIUM", "HIGH", "EXTREME"]
UnifiedTradeAction = Literal["ALLOW", "REDUCE_RISK", "BLOCK", "WAIT_FOR_STABILIZATION"]


class UnifiedNewsRiskDecision(BaseModel):
    decision_id: str = Field(default_factory=lambda: f"unified-news-{uuid4().hex}")
    symbol: str = "XAUUSD"
    calendar_risk_level: UnifiedRiskLevel = "LOW"
    headline_risk_level: UnifiedRiskLevel = "LOW"
    macro_risk_level: UnifiedRiskLevel = "LOW"
    final_risk_level: UnifiedRiskLevel = "LOW"
    final_trade_action: UnifiedTradeAction = "ALLOW"
    confidence_adjustment: float = 0.0
    confidence_cap: float | None = None
    blocking_reasons: list[str] = Field(default_factory=list)
    supportive_reasons: list[str] = Field(default_factory=list)
    client_summary: str = "No unified news, macro, or headline risk is blocking XAUUSD analysis."
    technical_summary: str = "Unified news risk ALLOW: all checked contexts are clear."
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)
