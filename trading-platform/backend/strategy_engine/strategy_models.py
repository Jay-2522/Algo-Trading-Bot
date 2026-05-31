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
BosDirection = Literal["BULLISH_BOS", "BEARISH_BOS", "NONE"]
ChochDirection = Literal["BULLISH_CHOCH", "BEARISH_CHOCH", "NONE"]
StructureQuality = Literal["HIGH", "MEDIUM", "LOW", "NONE"]
StrategyAction = Literal["BUY", "SELL", "WAIT"]
FVGDirection = Literal["BULLISH", "BEARISH"]
OrderBlockDirection = Literal["BULLISH", "BEARISH"]
MarketRegime = Literal[
    "TRENDING",
    "RANGING",
    "HIGH_VOLATILITY",
    "LOW_VOLATILITY",
    "NEWS_VOLATILITY_PLACEHOLDER",
    "UNCLEAR",
]
Tradeability = Literal["HIGH", "MEDIUM", "LOW", "AVOID"]
RiskMode = Literal["NORMAL", "REDUCED_RISK", "NO_TRADE"]
TradeQuality = Literal["A_PLUS", "A", "B", "C", "NO_TRADE"]


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


class EURUSDLiquidityContext(BaseModel):
    symbol: str = "EURUSD"
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
    sweep_direction: SweepDirection = "NONE"
    confidence: float = 0.0
    warnings: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)


class EURUSDStructureContext(BaseModel):
    symbol: str = "EURUSD"
    swing_highs: list[dict[str, Any]] = Field(default_factory=list)
    swing_lows: list[dict[str, Any]] = Field(default_factory=list)
    latest_swing_high: dict[str, Any] | None = None
    latest_swing_low: dict[str, Any] | None = None
    bos_detected: bool = False
    choch_detected: bool = False
    bos_direction: BosDirection = "NONE"
    choch_direction: ChochDirection = "NONE"
    structure_shift_detected: bool = False
    break_level: float | None = None
    break_price: float | None = None
    break_candle_time: str | None = None
    post_sweep_confirmation: bool = False
    structure_strength: float = 0.0
    structure_quality: StructureQuality = "NONE"
    structure_bias: StructureBias = "NEUTRAL"
    confirmation_reason: str = "No EURUSD BOS or CHOCH confirmation detected."
    confidence: float = 0.0
    warnings: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)


class EURUSDFairValueGap(BaseModel):
    fvg_id: str
    symbol: str = "EURUSD"
    direction: FVGDirection
    start_time: str
    end_time: str
    upper_bound: float
    lower_bound: float
    midpoint: float
    size: float
    fill_percentage: float = 0.0
    mitigated: bool = False
    active: bool = True
    displacement_strength: float = 0.0
    quality: StructureQuality = "NONE"
    aligned_with_structure: bool = False
    aligned_with_liquidity: bool = False
    warnings: list[str] = Field(default_factory=list)


class EURUSDFVGContext(BaseModel):
    symbol: str = "EURUSD"
    fair_value_gaps: list[EURUSDFairValueGap] = Field(default_factory=list)
    latest_fvg: EURUSDFairValueGap | None = None
    bullish_fvg_detected: bool = False
    bearish_fvg_detected: bool = False
    active_fvg_detected: bool = False
    fvg_direction: FVGDirection | Literal["NONE"] = "NONE"
    fvg_quality: StructureQuality = "NONE"
    fvg_confidence: float = 0.0
    fvg_alignment_reason: str = "No active EURUSD FVG alignment detected."
    warnings: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)


class SMCStructureContext(BaseModel):
    symbol: str
    swing_highs: list[dict[str, Any]] = Field(default_factory=list)
    swing_lows: list[dict[str, Any]] = Field(default_factory=list)
    latest_swing_high: dict[str, Any] | None = None
    latest_swing_low: dict[str, Any] | None = None
    bos_detected: bool = False
    choch_detected: bool = False
    fvg_detected: bool = False
    order_block_detected: bool = False
    bos_direction: BosDirection = "NONE"
    choch_direction: ChochDirection = "NONE"
    structure_shift_detected: bool = False
    break_level: float | None = None
    break_price: float | None = None
    break_candle_time: str | None = None
    post_sweep_confirmation: bool = False
    structure_strength: float = 0.0
    structure_quality: StructureQuality = "NONE"
    confirmation_reason: str = "No BOS or CHOCH confirmation detected."
    fair_value_gaps: list["FairValueGap"] = Field(default_factory=list)
    latest_fvg: "FairValueGap | None" = None
    bullish_fvg_detected: bool = False
    bearish_fvg_detected: bool = False
    active_fvg_detected: bool = False
    fvg_direction: FVGDirection | Literal["NONE"] = "NONE"
    fvg_quality: StructureQuality = "NONE"
    fvg_confidence: float = 0.0
    fvg_alignment_reason: str = "No active FVG alignment detected."
    order_blocks: list["OrderBlock"] = Field(default_factory=list)
    latest_order_block: "OrderBlock | None" = None
    bullish_order_block_detected: bool = False
    bearish_order_block_detected: bool = False
    active_order_block_detected: bool = False
    order_block_direction: OrderBlockDirection | Literal["NONE"] = "NONE"
    order_block_quality: StructureQuality = "NONE"
    order_block_confidence: float = 0.0
    order_block_alignment_reason: str = "No active order block alignment detected."
    structure_bias: StructureBias = "NEUTRAL"
    confidence: float = 0.0
    warnings: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)


class FairValueGap(BaseModel):
    fvg_id: str
    symbol: str
    direction: FVGDirection
    start_time: str
    end_time: str
    upper_bound: float
    lower_bound: float
    midpoint: float
    size: float
    fill_percentage: float = 0.0
    mitigated: bool = False
    active: bool = True
    displacement_strength: float = 0.0
    quality: StructureQuality = "NONE"
    aligned_with_structure: bool = False
    aligned_with_liquidity: bool = False
    warnings: list[str] = Field(default_factory=list)


class OrderBlock(BaseModel):
    order_block_id: str
    symbol: str
    direction: OrderBlockDirection
    creation_time: str
    upper_bound: float
    lower_bound: float
    midpoint: float
    active: bool = True
    fresh: bool = True
    mitigated: bool = False
    broken: bool = False
    fill_percentage: float = 0.0
    remaining_effectiveness: float = 100.0
    strength: float = 0.0
    quality: StructureQuality = "NONE"
    aligned_with_structure: bool = False
    aligned_with_liquidity: bool = False
    aligned_with_fvg: bool = False
    warnings: list[str] = Field(default_factory=list)


class MarketRegimeContext(BaseModel):
    symbol: str
    regime: MarketRegime = "UNCLEAR"
    trend_strength: float = 0.0
    volatility_score: float = 0.0
    range_score: float = 0.0
    atr_state: VolatilityState = "NORMAL"
    ema_alignment: TrendBias = "NEUTRAL"
    session_alignment: bool = False
    tradeability: Tradeability = "AVOID"
    risk_mode: RiskMode = "NO_TRADE"
    confidence: float = 0.0
    warnings: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)


class ConfluenceScoreBreakdown(BaseModel):
    session_score: float = 0.0
    indicator_score: float = 0.0
    liquidity_score: float = 0.0
    structure_score: float = 0.0
    fvg_score: float = 0.0
    order_block_score: float = 0.0
    regime_score: float = 0.0
    total_score: float = 0.0
    confidence: float = 0.0
    trade_quality: TradeQuality = "NO_TRADE"
    missing_confirmations: list[str] = Field(default_factory=list)
    aligned_confirmations: list[str] = Field(default_factory=list)
    risk_mode: RiskMode = "NO_TRADE"
    warnings: list[str] = Field(default_factory=list)


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
    regime_context: MarketRegimeContext
    confluence_score: ConfluenceScoreBreakdown
    trade_quality: TradeQuality = "NO_TRADE"
    aligned_confirmations: list[str] = Field(default_factory=list)
    missing_confirmations: list[str] = Field(default_factory=list)
    headline_context: dict[str, Any] = Field(default_factory=dict)
    headline_filter_decision: dict[str, Any] = Field(default_factory=dict)
    unified_news_decision: dict[str, Any] = Field(default_factory=dict)
    client_summary: str = ""
    technical_summary: str = ""
    risk_notes: list[str] = Field(default_factory=list)
    execution_allowed: bool = False
    reason: str
    timestamp: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        self.execution_allowed = False


class EURUSDStrategySignal(BaseModel):
    signal_id: str
    symbol: str
    action: StrategyAction = "WAIT"
    confidence: float = 0.0
    trend_bias: TrendBias = "NEUTRAL"
    session_context: MarketSessionContext
    indicator_context: IndicatorContext
    liquidity_context: EURUSDLiquidityContext | None = None
    structure_context: EURUSDStructureContext | None = None
    fvg_context: EURUSDFVGContext | None = None
    execution_allowed: bool = False
    reason: str
    timestamp: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        self.execution_allowed = False
