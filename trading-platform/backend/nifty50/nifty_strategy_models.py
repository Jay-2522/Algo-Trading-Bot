from datetime import datetime, timezone

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class NIFTYLiquidityContext(BaseModel):
    previous_day_high: float | None = None
    previous_day_low: float | None = None
    weekly_high: float | None = None
    weekly_low: float | None = None
    equal_highs: list[float] = Field(default_factory=list)
    equal_lows: list[float] = Field(default_factory=list)
    liquidity_pools: list[dict] = Field(default_factory=list)
    sweep_detected: bool = False
    sweep_direction: str = "NONE"
    confidence: float = 0.0
    placeholder: bool = True
    timestamp: datetime = Field(default_factory=utc_now)


class NIFTYStructureContext(BaseModel):
    swing_highs: list[float] = Field(default_factory=list)
    swing_lows: list[float] = Field(default_factory=list)
    bos_detected: bool = False
    choch_detected: bool = False
    structure_bias: str = "NEUTRAL"
    structure_strength: float = 0.0
    placeholder: bool = True
    timestamp: datetime = Field(default_factory=utc_now)


class NIFTYFVGContext(BaseModel):
    fair_value_gaps: list[dict] = Field(default_factory=list)
    active_fvg_detected: bool = False
    fvg_direction: str = "NONE"
    confidence: float = 0.0
    placeholder: bool = True
    timestamp: datetime = Field(default_factory=utc_now)


class NIFTYOrderBlockContext(BaseModel):
    bullish_order_blocks: list[dict] = Field(default_factory=list)
    bearish_order_blocks: list[dict] = Field(default_factory=list)
    active_order_block: dict | None = None
    confidence: float = 0.0
    placeholder: bool = True
    timestamp: datetime = Field(default_factory=utc_now)


class NIFTYStrategySnapshot(BaseModel):
    symbol: str = "NIFTY50"
    liquidity_context: NIFTYLiquidityContext = Field(default_factory=NIFTYLiquidityContext)
    structure_context: NIFTYStructureContext = Field(default_factory=NIFTYStructureContext)
    fvg_context: NIFTYFVGContext = Field(default_factory=NIFTYFVGContext)
    order_block_context: NIFTYOrderBlockContext = Field(default_factory=NIFTYOrderBlockContext)
    regime: str = "UNKNOWN"
    confidence: float = 0.0
    strategy_bias: str = "NEUTRAL"
    placeholder: bool = True
    timestamp: datetime = Field(default_factory=utc_now)
