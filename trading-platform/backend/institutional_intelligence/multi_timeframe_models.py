from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


Direction = Literal["BULLISH", "BEARISH", "NEUTRAL", "CONFLICTED"]


class TimeframeDirectionalBias(BaseModel):
    timeframe: Literal["M5", "M15", "H1", "H4"]
    direction: Direction = "NEUTRAL"
    confidence: float = Field(default=0.0, ge=0.0, le=100.0)
    structure_bias: str = "UNCLEAR"
    confluence_score: float = Field(default=0.0, ge=0.0, le=100.0)
    dominant_event: str | None = None
    narrative: str = ""


class InstitutionalNarrative(BaseModel):
    symbol: str
    macro_story: str = ""
    directional_story: str = ""
    execution_story: str = ""
    precision_story: str = ""
    summary: str = ""
    bullish_factors: list[str] = Field(default_factory=list)
    bearish_factors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class MultiTimeframeAlignment(BaseModel):
    symbol: str
    macro_bias: TimeframeDirectionalBias
    directional_bias: TimeframeDirectionalBias
    execution_bias: TimeframeDirectionalBias
    precision_bias: TimeframeDirectionalBias
    overall_direction: Direction = "NEUTRAL"
    alignment_score: float = Field(default=0.0, ge=0.0, le=100.0)
    confidence: float = Field(default=0.0, ge=0.0, le=100.0)
    alignment_quality: Literal[
        "FULLY_ALIGNED",
        "STRONGLY_ALIGNED",
        "PARTIALLY_ALIGNED",
        "MIXED",
        "CONFLICTED",
    ] = "MIXED"
    conflicts: list[str] = Field(default_factory=list)
    confirmations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    institutional_narrative: InstitutionalNarrative | None = None
    timestamp: datetime = Field(default_factory=utc_now)


class TimeframeConflictResult(BaseModel):
    conflicts: list[str] = Field(default_factory=list)
    severity: Literal["NONE", "LOW", "MODERATE", "HIGH", "SEVERE"] = "NONE"
    affected_timeframes: list[str] = Field(default_factory=list)


class BiasResolutionResult(BaseModel):
    direction: Direction = "NEUTRAL"
    confidence: float = Field(default=0.0, ge=0.0, le=100.0)
    confirmations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
