from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FairValueGap(BaseModel):
    fvg_id: str = Field(default_factory=lambda: f"FVG-{uuid4().hex}")
    symbol: str
    timeframe: str
    direction: Literal["BULLISH", "BEARISH"]
    start_index: int = Field(ge=0)
    middle_index: int = Field(ge=0)
    end_index: int = Field(ge=0)
    timestamp: datetime
    gap_high: float
    gap_low: float
    gap_size: float = Field(ge=0.0)
    mitigation_status: Literal["FRESH", "PARTIAL", "MITIGATED"] = "FRESH"
    mitigation_percent: float = Field(default=0.0, ge=0.0, le=100.0)
    strength: float = Field(default=0.0, ge=0.0, le=100.0)
    fresh: bool = True
    valid: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class FVGContext(BaseModel):
    symbol: str
    timeframe: str
    fvgs: list[FairValueGap] = Field(default_factory=list)
    fresh_fvgs: list[FairValueGap] = Field(default_factory=list)
    mitigated_fvgs: list[FairValueGap] = Field(default_factory=list)
    high_quality_fvgs: list[FairValueGap] = Field(default_factory=list)
    latest_fvg: FairValueGap | None = None
    bullish_fvgs: list[FairValueGap] = Field(default_factory=list)
    bearish_fvgs: list[FairValueGap] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=100.0)
    timestamp: datetime = Field(default_factory=utc_now)


class FVGMitigationResult(BaseModel):
    status: Literal["FRESH", "PARTIAL", "MITIGATED"]
    mitigation_percent: float = Field(default=0.0, ge=0.0, le=100.0)
    touched: bool = False
    fully_mitigated: bool = False
    reason: str


class FVGStrengthScore(BaseModel):
    score: float = Field(default=0.0, ge=0.0, le=100.0)
    gap_size_score: float = Field(default=0.0, ge=0.0, le=25.0)
    displacement_score: float = Field(default=0.0, ge=0.0, le=25.0)
    freshness_score: float = Field(default=0.0, ge=0.0, le=20.0)
    mitigation_score: float = Field(default=0.0, ge=0.0, le=20.0)
    confluence_score: float = Field(default=0.0, ge=0.0, le=10.0)
    reason: str
