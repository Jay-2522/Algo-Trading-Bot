from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MarketNarrative(BaseModel):
    symbol: str
    timeframe: str
    headline: str
    summary: str
    institutional_bias: str = "UNCLEAR"
    market_state: str = "UNCLEAR"
    setup_state: str = "NO_SETUP"
    simulation_state: str = "NO_VALID_SETUP"
    key_drivers: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    recommended_action: Literal["MONITOR", "WAIT", "AVOID", "READY_FOR_SIMULATION", "MANAGE_POSITION"] = "MONITOR"
    confidence: float = Field(default=0.0, ge=0.0, le=100.0)
    timestamp: datetime = Field(default_factory=utc_now)


class InstitutionalReasoningReport(BaseModel):
    symbol: str
    timeframe: str
    narrative: MarketNarrative
    executive_summary: str = ""
    detailed_reasoning: str = ""
    bullish_case: list[str] = Field(default_factory=list)
    bearish_case: list[str] = Field(default_factory=list)
    neutral_case: list[str] = Field(default_factory=list)
    invalidation_notes: list[str] = Field(default_factory=list)
    timing_notes: list[str] = Field(default_factory=list)
    risk_notes: list[str] = Field(default_factory=list)
    client_friendly_summary: str = ""
    dashboard_summary: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=100.0)
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)


class ReasoningQualityCheck(BaseModel):
    passed: bool = False
    clarity_score: float = Field(default=0.0, ge=0.0, le=100.0)
    contradiction_detected: bool = False
    missing_sections: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
