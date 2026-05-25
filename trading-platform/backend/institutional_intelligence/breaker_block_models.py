from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class BreakerBlock(BaseModel):
    breaker_id: str = Field(default_factory=lambda: f"BRK-{uuid4().hex}")
    symbol: str
    timeframe: str
    direction: Literal["BULLISH", "BEARISH"]
    source_order_block_id: str
    candle_index: int = Field(ge=0)
    timestamp: datetime
    original_ob_direction: Literal["BULLISH", "BEARISH"]
    break_price: float
    zone_high: float
    zone_low: float
    structure_shift_confirmed: bool = False
    mitigation_status: Literal["FRESH", "PARTIALLY_MITIGATED", "MITIGATED"] = "FRESH"
    mitigation_percent: float = Field(default=0.0, ge=0.0, le=100.0)
    fresh: bool = True
    valid: bool = False
    strength: float = Field(default=0.0, ge=0.0, le=100.0)
    related_fvg: str | None = None
    related_sweep: str | None = None
    structure_bias: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class BreakerBlockValidationResult(BaseModel):
    valid: bool
    validation_reason: str
    validation_confidence: float = Field(default=0.0, ge=0.0, le=100.0)


class BreakerBlockMitigationResult(BaseModel):
    status: Literal["FRESH", "PARTIALLY_MITIGATED", "MITIGATED"]
    mitigation_percent: float = Field(default=0.0, ge=0.0, le=100.0)
    touched: bool = False
    fully_mitigated: bool = False
    reason: str


class BreakerBlockStrengthScore(BaseModel):
    score: float = Field(default=0.0, ge=0.0, le=100.0)
    displacement_score: float = Field(default=0.0, ge=0.0, le=25.0)
    structure_shift_score: float = Field(default=0.0, ge=0.0, le=25.0)
    freshness_score: float = Field(default=0.0, ge=0.0, le=20.0)
    mitigation_score: float = Field(default=0.0, ge=0.0, le=15.0)
    confluence_score: float = Field(default=0.0, ge=0.0, le=15.0)
    reason: str


class BreakerBlockContext(BaseModel):
    symbol: str
    timeframe: str
    breaker_blocks: list[BreakerBlock] = Field(default_factory=list)
    fresh_breakers: list[BreakerBlock] = Field(default_factory=list)
    mitigated_breakers: list[BreakerBlock] = Field(default_factory=list)
    high_quality_breakers: list[BreakerBlock] = Field(default_factory=list)
    latest_breaker: BreakerBlock | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=100.0)
    timestamp: datetime = Field(default_factory=utc_now)
