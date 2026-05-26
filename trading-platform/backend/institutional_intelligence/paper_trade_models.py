from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PaperTradeCandidate(BaseModel):
    candidate_id: str = Field(default_factory=lambda: f"PPC-{uuid4().hex}")
    symbol: str
    timeframe: str
    direction: Literal["BUY", "SELL"]
    source_decision_id: str
    source_intent_id: str
    entry_low: float
    entry_high: float
    invalidation_level: float
    target_level: float
    estimated_rr: float = Field(default=0.0, ge=0.0)
    quality_score: float = Field(default=0.0, ge=0.0, le=100.0)
    status: Literal["PENDING", "ACTIVE", "CANCELLED", "EXPIRED", "CLOSED"] = "PENDING"
    created_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime
    simulation_only: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class PaperTradePosition(BaseModel):
    position_id: str = Field(default_factory=lambda: f"PPP-{uuid4().hex}")
    candidate_id: str
    symbol: str
    direction: Literal["BUY", "SELL"]
    entry_price: float
    invalidation_level: float
    target_level: float
    opened_at: datetime = Field(default_factory=utc_now)
    closed_at: datetime | None = None
    status: Literal["ACTIVE", "CLOSED"] = "ACTIVE"
    outcome: Literal["WIN", "LOSS", "BREAKEVEN", "EXPIRED", "CANCELLED", "OPEN"] = "OPEN"
    pnl_points: float = 0.0
    rr_result: float = 0.0
    close_reason: str | None = None
    simulation_only: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class PaperTradeLifecycleContext(BaseModel):
    symbol: str
    timeframe: str
    candidates: list[PaperTradeCandidate] = Field(default_factory=list)
    active_positions: list[PaperTradePosition] = Field(default_factory=list)
    closed_positions: list[PaperTradePosition] = Field(default_factory=list)
    latest_candidate: PaperTradeCandidate | None = None
    latest_position: PaperTradePosition | None = None
    lifecycle_status: Literal[
        "NO_CANDIDATE",
        "WAITING_FOR_ENTRY",
        "POSITION_ACTIVE",
        "POSITION_CLOSED",
        "BLOCKED",
    ] = "NO_CANDIDATE"
    summary: str = ""
    timestamp: datetime = Field(default_factory=utc_now)
