from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


NIFTYAction = Literal["BUY", "SELL", "WAIT"]
NIFTYOrderType = Literal["MARKET", "LIMIT"]
NIFTYProductType = Literal["INTRADAY", "DELIVERY_PLACEHOLDER"]
NIFTYPreviewStatus = Literal["READY_FOR_REVIEW", "REJECTED", "BLOCKED_EXECUTION_DISABLED", "BROKER_NOT_SELECTED", "FAILED_SAFE"]


class NIFTYExecutionIntent(BaseModel):
    intent_id: str = Field(default_factory=lambda: f"nifty-intent-{uuid4().hex[:12]}")
    candidate_id: str
    symbol: str = "NIFTY50"
    action: NIFTYAction
    quantity: int = 1
    order_type: NIFTYOrderType = "MARKET"
    product_type: NIFTYProductType = "INTRADAY"
    exchange: str = "NSE"
    broker_id: str | None = None
    strategy_confidence: float = 0.0
    risk_decision_id: str
    execution_allowed: bool = False
    simulation_only: bool = True
    live_execution_enabled: bool = False
    broker_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)

    def model_post_init(self, __context: Any) -> None:
        self.execution_allowed = False
        self.simulation_only = True
        self.live_execution_enabled = False
        self.broker_execution_enabled = False


class NIFTYOrderPreview(BaseModel):
    preview_id: str = Field(default_factory=lambda: f"nifty-preview-{uuid4().hex[:12]}")
    intent_id: str
    broker_id: str | None = None
    symbol: str = "NIFTY50"
    exchange: str = "NSE"
    action: NIFTYAction
    quantity: int
    order_type: NIFTYOrderType
    product_type: NIFTYProductType
    estimated_value: float = 0.0
    charges_placeholder: float = 0.0
    margin_required_placeholder: float = 0.0
    preview_status: NIFTYPreviewStatus = "BLOCKED_EXECUTION_DISABLED"
    rejection_reasons: list[str] = Field(default_factory=list)
    simulation_only: bool = True
    broker_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)


class NIFTYExecutionAuditEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"nifty-audit-{uuid4().hex[:12]}")
    stage: str
    status: str
    entity_id: str
    message: str
    timestamp: datetime = Field(default_factory=utc_now)
