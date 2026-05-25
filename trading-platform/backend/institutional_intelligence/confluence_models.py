from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from backend.institutional_intelligence.breaker_block_models import BreakerBlockContext
from backend.institutional_intelligence.fair_value_gap_models import FVGContext
from backend.institutional_intelligence.liquidity_sweep_models import SweepContext
from backend.institutional_intelligence.order_block_models import OrderBlockContext
from backend.institutional_intelligence.smc_models import InstitutionalContext
from backend.institutional_intelligence.structure_shift_models import StructureShiftContext


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ConfluenceComponentScore(BaseModel):
    component: Literal[
        "STRUCTURE_BIAS",
        "LIQUIDITY_SWEEP",
        "FVG",
        "ORDER_BLOCK",
        "BREAKER_BLOCK",
        "STRUCTURE_SHIFT",
        "PREMIUM_DISCOUNT",
        "DISPLACEMENT",
        "SESSION",
        "RISK",
    ]
    direction: Literal["BULLISH", "BEARISH", "NEUTRAL"]
    score: float = Field(default=0.0, ge=0.0, le=100.0)
    weight: float = Field(ge=0.0, le=100.0)
    weighted_score: float = Field(default=0.0, ge=0.0, le=100.0)
    reason: str


class InstitutionalConfluenceScore(BaseModel):
    symbol: str
    timeframe: str
    bullish_score: float = Field(default=0.0, ge=0.0, le=100.0)
    bearish_score: float = Field(default=0.0, ge=0.0, le=100.0)
    neutral_score: float = Field(default=0.0, ge=0.0, le=100.0)
    overall_score: float = Field(default=0.0, ge=0.0, le=100.0)
    dominant_direction: Literal["BULLISH", "BEARISH", "NEUTRAL", "CONFLICTED"] = "NEUTRAL"
    confidence: float = Field(default=0.0, ge=0.0, le=100.0)
    setup_quality: Literal["A_PLUS", "A", "B", "C", "LOW_QUALITY", "NO_TRADE"] = "NO_TRADE"
    trade_readiness: Literal[
        "READY_FOR_SIMULATION",
        "WAIT_FOR_CONFIRMATION",
        "AVOID",
        "BLOCKED_BY_RISK",
        "NO_SETUP",
    ] = "NO_SETUP"
    component_scores: list[ConfluenceComponentScore] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    explanation: str = ""
    timestamp: datetime = Field(default_factory=utc_now)


class ConfluenceContext(BaseModel):
    symbol: str
    timeframe: str
    institutional_context: InstitutionalContext
    sweep_context: SweepContext
    fvg_context: FVGContext
    order_block_context: OrderBlockContext
    breaker_context: BreakerBlockContext
    structure_shift_context: StructureShiftContext
    confluence_score: InstitutionalConfluenceScore
    timestamp: datetime = Field(default_factory=utc_now)
