from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class LiquiditySweep(BaseModel):
    sweep_id: str = Field(default_factory=lambda: f"SWP-{uuid4().hex}")
    symbol: str
    timeframe: str
    sweep_type: Literal[
        "EQUAL_HIGH_SWEEP",
        "EQUAL_LOW_SWEEP",
        "PREVIOUS_HIGH_SWEEP",
        "PREVIOUS_LOW_SWEEP",
        "EXTERNAL_LIQUIDITY_SWEEP",
        "INTERNAL_LIQUIDITY_SWEEP",
    ]
    direction: Literal["BULLISH", "BEARISH"]
    swept_level: float
    sweep_price: float
    candle_index: int = Field(ge=0)
    timestamp: datetime
    close_back_inside: bool
    wick_rejection: bool
    strength: float = Field(default=0.0, ge=0.0, le=100.0)
    valid: bool
    related_liquidity_pool: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class SweepValidationResult(BaseModel):
    valid: bool
    close_back_inside: bool
    wick_rejection: bool
    rejection_strength: float = Field(default=0.0, ge=0.0, le=100.0)
    reason: str


class SweepContext(BaseModel):
    symbol: str
    timeframe: str
    sweeps: list[LiquiditySweep] = Field(default_factory=list)
    latest_sweep: LiquiditySweep | None = None
    bullish_sweeps: list[LiquiditySweep] = Field(default_factory=list)
    bearish_sweeps: list[LiquiditySweep] = Field(default_factory=list)
    high_quality_sweeps: list[LiquiditySweep] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=100.0)
    timestamp: datetime = Field(default_factory=utc_now)
