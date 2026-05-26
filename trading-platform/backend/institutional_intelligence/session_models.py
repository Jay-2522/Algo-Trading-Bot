from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


SessionName = Literal["ASIAN", "LONDON", "NEW_YORK"]


class TradingSessionRange(BaseModel):
    session_name: SessionName
    start_time_utc: str
    end_time_utc: str
    high: float | None = None
    low: float | None = None
    midpoint: float | None = None
    range_size: float = Field(default=0.0, ge=0.0)
    candles_count: int = Field(default=0, ge=0)
    valid: bool = False


class KillzoneStatus(BaseModel):
    active_killzone: bool = False
    killzone_name: Literal["LONDON_OPEN", "NEW_YORK_OPEN", "LONDON_CLOSE", "NONE"] = "NONE"
    session_name: Literal["LONDON", "NEW_YORK", "NONE"] = "NONE"
    start_time_utc: str | None = None
    end_time_utc: str | None = None
    high_liquidity_window: bool = False
    quality: Literal["HIGH", "NORMAL", "LOW"] = "LOW"


class SessionLiquidityProfile(BaseModel):
    session_name: SessionName
    liquidity_quality: Literal["HIGH", "NORMAL", "LOW", "POOR"] = "POOR"
    volatility_quality: Literal["HIGH", "NORMAL", "LOW", "POOR"] = "POOR"
    range_expansion: float = Field(default=0.0, ge=0.0)
    sweep_detected: bool = False
    breakout_detected: bool = False
    confidence: float = Field(default=0.0, ge=0.0, le=100.0)


class SessionManipulationSignal(BaseModel):
    signal_id: str
    manipulation_type: Literal[
        "ASIAN_HIGH_SWEEP",
        "ASIAN_LOW_SWEEP",
        "LONDON_FAKEOUT",
        "NEW_YORK_REVERSAL",
        "NONE",
    ]
    direction: Literal["BULLISH", "BEARISH", "NEUTRAL"]
    session_name: SessionName
    swept_level: float | None = None
    confirmation: bool = False
    confidence: float = Field(default=0.0, ge=0.0, le=100.0)
    timestamp: datetime = Field(default_factory=utc_now)


class SessionIntelligenceContext(BaseModel):
    symbol: str
    timeframe: str
    current_session: str
    active_killzone: KillzoneStatus
    asian_range: TradingSessionRange
    london_range: TradingSessionRange
    new_york_range: TradingSessionRange
    liquidity_profile: SessionLiquidityProfile
    manipulation_signals: list[SessionManipulationSignal] = Field(default_factory=list)
    session_quality_score: float = Field(default=0.0, ge=0.0, le=100.0)
    trade_timing_readiness: Literal[
        "HIGH_QUALITY_WINDOW",
        "WAIT_FOR_KILLZONE",
        "AVOID_LOW_LIQUIDITY",
        "AVOID_NEWS_WINDOW",
        "NORMAL_MONITORING",
    ] = "NORMAL_MONITORING"
    warnings: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)
