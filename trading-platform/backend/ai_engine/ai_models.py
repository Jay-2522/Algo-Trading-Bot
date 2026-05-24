from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class MarketRegime(BaseModel):
    """Classified market environment used for advisory decisions."""

    regime: Literal["TRENDING", "RANGING", "VOLATILE", "LOW_LIQUIDITY", "NEWS_RISK"]
    volatility_level: Literal["LOW", "NORMAL", "HIGH", "EXTREME"]
    liquidity_quality: str
    trend_strength: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=100)


class SignalScore(BaseModel):
    """Normalized quality scores for the setup evaluation factors."""

    trend_score: float = Field(ge=0, le=100)
    liquidity_score: float = Field(ge=0, le=100)
    structure_score: float = Field(ge=0, le=100)
    session_score: float = Field(ge=0, le=100)
    volatility_score: float = Field(ge=0, le=100)
    spread_score: float = Field(ge=0, le=100)
    risk_score: float = Field(ge=0, le=100)
    overall_score: float = Field(ge=0, le=100)


class TradeDecision(BaseModel):
    """Advisory trade-quality outcome; it is never an execution instruction."""

    symbol: str
    action: Literal["BUY", "SELL", "WAIT", "AVOID"]
    confidence: float = Field(ge=0, le=100)
    approved: bool
    rejection_reason: str | None = None
    regime: MarketRegime
    signal_score: SignalScore
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DecisionExplanation(BaseModel):
    summary: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

