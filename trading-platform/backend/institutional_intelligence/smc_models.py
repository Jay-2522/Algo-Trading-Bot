from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SwingPoint(BaseModel):
    index: int = Field(ge=0)
    timestamp: datetime
    price: float
    type: Literal["HIGH", "LOW"]
    strength: float = Field(default=0.0, ge=0.0)


class LiquidityPool(BaseModel):
    pool_id: str = Field(default_factory=lambda: f"LIQ-{uuid4().hex}")
    symbol: str
    price_level: float
    liquidity_type: Literal[
        "EQUAL_HIGHS",
        "EQUAL_LOWS",
        "PREVIOUS_HIGH",
        "PREVIOUS_LOW",
        "INTERNAL_LIQUIDITY",
        "EXTERNAL_LIQUIDITY",
    ]
    strength: float = Field(default=0.0, ge=0.0)
    related_swings: list[int] = Field(default_factory=list)
    swept: bool = False
    timestamp: datetime = Field(default_factory=utc_now)


class StructureBias(BaseModel):
    bias: Literal["BULLISH", "BEARISH", "RANGING", "UNCLEAR"] = "UNCLEAR"
    higher_highs: int = 0
    higher_lows: int = 0
    lower_highs: int = 0
    lower_lows: int = 0
    confidence: float = Field(default=0.0, ge=0.0, le=100.0)


class PremiumDiscountZone(BaseModel):
    range_high: float = 0.0
    range_low: float = 0.0
    equilibrium: float = 0.0
    current_price: float = 0.0
    zone: Literal["PREMIUM", "DISCOUNT", "EQUILIBRIUM"] = "EQUILIBRIUM"


class DisplacementMove(BaseModel):
    direction: Literal["BULLISH", "BEARISH"]
    start_index: int = Field(ge=0)
    end_index: int = Field(ge=0)
    magnitude: float = Field(ge=0.0)
    candle_count: int = Field(default=1, ge=1)
    valid: bool = True


class InstitutionalContext(BaseModel):
    symbol: str
    timeframe: str
    swings: list[SwingPoint] = Field(default_factory=list)
    liquidity_pools: list[LiquidityPool] = Field(default_factory=list)
    structure_bias: StructureBias = Field(default_factory=StructureBias)
    premium_discount: PremiumDiscountZone = Field(default_factory=PremiumDiscountZone)
    displacement: list[DisplacementMove] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=100.0)
    timestamp: datetime = Field(default_factory=utc_now)
