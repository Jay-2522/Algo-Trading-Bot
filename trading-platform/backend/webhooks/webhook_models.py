from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class TradingViewWebhookPayload(BaseModel):
    symbol: str | None = None
    action: str | None = None
    timeframe: str | None = None
    strategy: str | None = None
    price: float | None = None
    timestamp: datetime | str | None = None
    confidence: float | None = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class NormalizedTradingSignal(BaseModel):
    signal_id: str = Field(default_factory=lambda: new_id("tv_signal"))
    canonical_symbol: str
    market_type: Literal["FOREX", "COMMODITY_CFD", "INDIAN_INDEX"]
    action: Literal["BUY", "SELL", "CLOSE", "ALERT_ONLY", "INVALID"]
    timeframe: str
    strategy_name: str | None = None
    signal_price: float | None = None
    confidence: float | None = None
    broker_targets: list[str] = Field(default_factory=list)
    routing_ready: bool = False
    orchestration_ready: bool = False
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)


class WebhookEventRecord(BaseModel):
    event_id: str = Field(default_factory=lambda: new_id("webhook_event"))
    source: str = "TRADINGVIEW"
    authenticated: bool = False
    valid: bool = False
    symbol: str | None = None
    action: str | None = None
    processing_status: Literal["RECEIVED", "VALIDATED", "NORMALIZED", "REJECTED", "FAILED_SAFE"] = "RECEIVED"
    issues: list[str] = Field(default_factory=list)
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)
