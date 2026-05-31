from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


BridgeStatus = Literal[
    "APPROVED_FOR_QUEUE_PREVIEW",
    "REJECTED_WAIT_SIGNAL",
    "REJECTED_LOW_CONFIDENCE",
    "REJECTED_EXECUTION_NOT_ALLOWED",
    "REJECTED_NEWS_RISK",
    "REJECTED_REGIME",
    "REJECTED_RISK_ENGINE",
    "FAILED_SAFE",
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StrategyExecutionIntent(BaseModel):
    intent_id: str = Field(default_factory=lambda: f"strategy_intent_{uuid4().hex[:12]}")
    source_signal_id: str
    symbol: str
    action: Literal["BUY", "SELL"]
    confidence: float
    suggested_lot: float = 0.01
    allocation_mode: str = "EQUAL"
    total_lot: float = 0.01
    strategy_name: str = "UNKNOWN_STRATEGY"
    reason: str = ""
    simulation_only: bool = True
    demo_execution: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)


class StrategyBridgeDecision(BaseModel):
    decision_id: str = Field(default_factory=lambda: f"bridge_decision_{uuid4().hex[:12]}")
    signal_id: str
    symbol: str
    action: str
    confidence: float = 0.0
    eligible: bool = False
    rejection_reasons: list[str] = Field(default_factory=list)
    mapped_intent: StrategyExecutionIntent | None = None
    queue_preview_id: str | None = None
    risk_decision_id: str | None = None
    bridge_status: BridgeStatus = "FAILED_SAFE"
    simulation_only: bool = True
    demo_execution: bool = True
    live_execution_enabled: bool = False
    broker_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)

    def model_post_init(self, __context: Any) -> None:
        self.simulation_only = True
        self.demo_execution = True
        self.live_execution_enabled = False
        self.broker_execution_enabled = False
