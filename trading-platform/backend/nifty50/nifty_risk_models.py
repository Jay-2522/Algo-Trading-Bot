from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


TradeQuality = Literal["A_PLUS", "A", "B", "C", "NO_TRADE"]
RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "BLOCKED"]
TradeAction = Literal["BUY", "SELL", "WAIT"]


class NIFTYRiskDecision(BaseModel):
    decision_id: str = Field(default_factory=lambda: f"nifty-risk-{uuid4().hex[:12]}")
    symbol: str = "NIFTY50"
    strategy_bias: str = "NEUTRAL"
    confidence: float = 0.0
    approved: bool = False
    trade_quality: TradeQuality = "NO_TRADE"
    risk_level: RiskLevel = "BLOCKED"
    rejection_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
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


class NIFTYTradeCandidate(BaseModel):
    candidate_id: str = Field(default_factory=lambda: f"nifty-candidate-{uuid4().hex[:12]}")
    symbol: str = "NIFTY50"
    action: TradeAction = "WAIT"
    confidence: float = 0.0
    strategy_bias: str = "NEUTRAL"
    trade_quality: TradeQuality = "NO_TRADE"
    risk_decision_id: str
    qualified: bool = False
    rejection_reasons: list[str] = Field(default_factory=list)
    execution_allowed: bool = False
    timestamp: datetime = Field(default_factory=utc_now)

    def model_post_init(self, __context: Any) -> None:
        self.execution_allowed = False
