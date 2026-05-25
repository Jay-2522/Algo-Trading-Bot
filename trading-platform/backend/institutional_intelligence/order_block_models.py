from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OrderBlock(BaseModel):
    ob_id: str = Field(default_factory=lambda: f"OB-{uuid4().hex}")
    symbol: str
    timeframe: str
    direction: Literal["BULLISH", "BEARISH"]
    candle_index: int = Field(ge=0)
    timestamp: datetime
    high: float
    low: float
    open: float
    close: float
    zone_high: float
    zone_low: float
    displacement_confirmed: bool = False
    bos_confirmed: bool = False
    mitigation_status: Literal["FRESH", "PARTIAL", "MITIGATED"] = "FRESH"
    mitigation_percent: float = Field(default=0.0, ge=0.0, le=100.0)
    fresh: bool = True
    valid: bool = False
    strength: float = Field(default=0.0, ge=0.0, le=100.0)
    related_fvg: str | None = None
    related_sweep: str | None = None
    structure_bias: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class OrderBlockValidationResult(BaseModel):
    valid: bool
    displacement_confirmed: bool
    bos_confirmed: bool
    reason: str
    confidence: float = Field(default=0.0, ge=0.0, le=100.0)


class OrderBlockMitigationResult(BaseModel):
    status: Literal["FRESH", "PARTIAL", "MITIGATED"]
    mitigation_percent: float = Field(default=0.0, ge=0.0, le=100.0)
    touched: bool = False
    fully_mitigated: bool = False
    reason: str


class OrderBlockStrengthScore(BaseModel):
    score: float = Field(default=0.0, ge=0.0, le=100.0)
    displacement_score: float = Field(default=0.0, ge=0.0, le=25.0)
    bos_score: float = Field(default=0.0, ge=0.0, le=25.0)
    freshness_score: float = Field(default=0.0, ge=0.0, le=20.0)
    mitigation_score: float = Field(default=0.0, ge=0.0, le=15.0)
    confluence_score: float = Field(default=0.0, ge=0.0, le=15.0)
    reason: str


class OrderBlockContext(BaseModel):
    symbol: str
    timeframe: str
    order_blocks: list[OrderBlock] = Field(default_factory=list)
    fresh_order_blocks: list[OrderBlock] = Field(default_factory=list)
    mitigated_order_blocks: list[OrderBlock] = Field(default_factory=list)
    high_quality_order_blocks: list[OrderBlock] = Field(default_factory=list)
    latest_order_block: OrderBlock | None = None
    bullish_order_blocks: list[OrderBlock] = Field(default_factory=list)
    bearish_order_blocks: list[OrderBlock] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=100.0)
    timestamp: datetime = Field(default_factory=utc_now)
