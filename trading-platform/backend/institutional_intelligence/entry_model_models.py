from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


ModelType = Literal[
    "SWEEP_FVG_CONTINUATION",
    "ORDER_BLOCK_RETRACEMENT",
    "BREAKER_RETEST",
    "MSS_REVERSAL",
    "LIQUIDITY_REVERSAL",
    "NO_TRADE",
]
Readiness = Literal["READY_FOR_SIMULATION", "WAIT_FOR_CONFIRMATION", "AVOID", "NO_SETUP"]


class InstitutionalEntryModel(BaseModel):
    model_id: str = Field(default_factory=lambda: f"ENT-{uuid4().hex}")
    symbol: str
    timeframe: str
    model_type: ModelType
    direction: Literal["BULLISH", "BEARISH", "NEUTRAL"]
    entry_zone_low: float | None = None
    entry_zone_high: float | None = None
    invalidation_level: float | None = None
    target_level: float | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=100.0)
    quality_score: float = Field(default=0.0, ge=0.0, le=100.0)
    readiness: Readiness = "WAIT_FOR_CONFIRMATION"
    supporting_factors: list[str] = Field(default_factory=list)
    blocking_factors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    related_sweep: Any = None
    related_fvg: Any = None
    related_order_block: Any = None
    related_breaker: Any = None
    related_structure_event: Any = None
    session_context: Any = None
    alignment_context: Any = None
    timestamp: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EntryModelContext(BaseModel):
    symbol: str
    timeframe: str
    models: list[InstitutionalEntryModel] = Field(default_factory=list)
    best_model: InstitutionalEntryModel | None = None
    bullish_models: list[InstitutionalEntryModel] = Field(default_factory=list)
    bearish_models: list[InstitutionalEntryModel] = Field(default_factory=list)
    ready_models: list[InstitutionalEntryModel] = Field(default_factory=list)
    waiting_models: list[InstitutionalEntryModel] = Field(default_factory=list)
    avoided_models: list[InstitutionalEntryModel] = Field(default_factory=list)
    overall_readiness: Readiness = "NO_SETUP"
    confidence: float = Field(default=0.0, ge=0.0, le=100.0)
    timestamp: datetime = Field(default_factory=utc_now)


class EntryModelValidationResult(BaseModel):
    valid: bool
    readiness: Readiness
    reason: str
    missing_requirements: list[str] = Field(default_factory=list)
    blocking_factors: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=100.0)


class EntryModelScore(BaseModel):
    score: float = Field(default=0.0, ge=0.0, le=100.0)
    alignment_score: float = Field(default=0.0, ge=0.0, le=20.0)
    confluence_score: float = Field(default=0.0, ge=0.0, le=25.0)
    session_score: float = Field(default=0.0, ge=0.0, le=15.0)
    structure_score: float = Field(default=0.0, ge=0.0, le=15.0)
    risk_score: float = Field(default=0.0, ge=0.0, le=10.0)
    freshness_score: float = Field(default=0.0, ge=0.0, le=15.0)
    reason: str = ""
