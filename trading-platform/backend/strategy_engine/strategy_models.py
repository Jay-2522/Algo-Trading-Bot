from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


SessionName = Literal["ASIAN", "LONDON", "NEW_YORK", "OVERLAP", "OFF_SESSION"]
SessionQuality = Literal["HIGH", "MEDIUM", "LOW"]
TrendBias = Literal["BULLISH", "BEARISH", "NEUTRAL"]
VolatilityState = Literal["LOW", "NORMAL", "HIGH", "EXTREME"]
SweepDirection = Literal["BUY_SIDE_SWEEP", "SELL_SIDE_SWEEP", "NONE"]
SweepQuality = Literal["HIGH", "MEDIUM", "LOW", "NONE"]
RejectionCandleType = Literal["PIN_BAR", "ENGULFING", "STRONG_CLOSE_BACK_INSIDE", "NONE"]
StructureBias = Literal["BULLISH", "BEARISH", "NEUTRAL"]
StrategyAction = Literal["BUY", "SELL", "WAIT"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MarketSessionContext(BaseModel):
    current_session: SessionName
    is_london_session: bool
    is_new_york_session: bool
    is_asian_session: bool
    session_quality: SessionQuality
    warnings: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)


class IndicatorContext(BaseModel):
    symbol: str
    timeframe: str
    ema_50: float | None = None
    ema_200: float | None = None
    trend_bias: TrendBias = "NEUTRAL"
    atr: float | None = None
    rsi: float | None = None
    macd_bias: TrendBias = "NEUTRAL"
    volatility_state: VolatilityState = "NORMAL"
    indicator_quality: SessionQuality = "LOW"
    warnings: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)


class LiquiditySweepContext(BaseModel):
    symbol: str
    asian_high: float | None = None
    asian_low: float | None = None
    previous_day_high: float | None = None
    previous_day_low: float | None = None
    equal_highs: list[dict[str, Any]] = Field(default_factory=list)
    equal_lows: list[dict[str, Any]] = Field(default_factory=list)
    liquidity_pools: list[dict[str, Any]] = Field(default_factory=list)
    swept_asian_high: bool = False
    swept_asian_low: bool = False
    swept_previous_high: bool = False
    swept_previous_low: bool = False
    active_sweep_level: str | None = None
    sweep_price: float | None = None
    rejection_detected: bool = False
    rejection_candle_type: RejectionCandleType = "NONE"
    sweep_strength: float = 0.0
    sweep_quality: SweepQuality = "NONE"
    session_alignment: bool = False
    volume_spike_detected: bool = False
    structure_confirmation_pending: bool = False
    sweep_direction: SweepDirection = "NONE"
    confidence: float = 0.0
    warnings: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)


class SMCStructureContext(BaseModel):
    symbol: str
    bos_detected: bool = False
    choch_detected: bool = False
    fvg_detected: bool = False
    order_block_detected: bool = False
    structure_bias: StructureBias = "NEUTRAL"
    confidence: float = 0.0
    warnings: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)


class XAUUSDStrategySignal(BaseModel):
    signal_id: str
    symbol: str
    action: StrategyAction
    confidence: float
    trend_bias: TrendBias
    session_context: MarketSessionContext
    indicator_context: IndicatorContext
    liquidity_context: LiquiditySweepContext
    smc_context: SMCStructureContext
    risk_notes: list[str] = Field(default_factory=list)
    execution_allowed: bool = False
    reason: str
    timestamp: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        self.execution_allowed = False
