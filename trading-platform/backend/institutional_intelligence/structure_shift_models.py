from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StructureEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"STR-{uuid4().hex}")
    symbol: str
    timeframe: str
    event_type: Literal["BOS", "CHOCH", "MSS"]
    direction: Literal["BULLISH", "BEARISH"]
    break_level: float
    break_price: float
    candle_index: int = Field(ge=0)
    timestamp: datetime
    swing_reference: dict[str, Any]
    close_confirmed: bool = False
    wick_break: bool = False
    continuation: bool = False
    reversal: bool = False
    valid: bool = False
    strength: float = Field(default=0.0, ge=0.0, le=100.0)
    related_sweep: str | None = None
    related_fvg: str | None = None
    related_order_block: str | None = None
    related_breaker: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class StructureShiftContext(BaseModel):
    symbol: str
    timeframe: str
    events: list[StructureEvent] = Field(default_factory=list)
    bos_events: list[StructureEvent] = Field(default_factory=list)
    choch_events: list[StructureEvent] = Field(default_factory=list)
    mss_events: list[StructureEvent] = Field(default_factory=list)
    latest_event: StructureEvent | None = None
    bullish_events: list[StructureEvent] = Field(default_factory=list)
    bearish_events: list[StructureEvent] = Field(default_factory=list)
    high_quality_events: list[StructureEvent] = Field(default_factory=list)
    current_structure_state: Literal["BULLISH", "BEARISH", "TRANSITIONING", "RANGING", "UNCLEAR"] = "UNCLEAR"
    confidence: float = Field(default=0.0, ge=0.0, le=100.0)
    timestamp: datetime = Field(default_factory=utc_now)


class StructureValidationResult(BaseModel):
    valid: bool
    close_confirmed: bool
    wick_break: bool
    break_strength: float = Field(default=0.0, ge=0.0, le=100.0)
    reason: str


class StructureStrengthScore(BaseModel):
    score: float = Field(default=0.0, ge=0.0, le=100.0)
    close_confirmation_score: float = Field(default=0.0, ge=0.0, le=25.0)
    swing_strength_score: float = Field(default=0.0, ge=0.0, le=20.0)
    displacement_score: float = Field(default=0.0, ge=0.0, le=20.0)
    confluence_score: float = Field(default=0.0, ge=0.0, le=20.0)
    continuation_reversal_score: float = Field(default=0.0, ge=0.0, le=15.0)
    reason: str
