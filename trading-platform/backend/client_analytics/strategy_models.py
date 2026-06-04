from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


Quality = Literal["HIGH", "MEDIUM", "LOW", "NONE", "PLACEHOLDER", "SMC_INTELLIGENCE_READY", "ANALYTICS_INTEGRATED"]


class StrategyPerformanceSummary(BaseModel):
    symbol: str
    total_signals: int = 0
    buy_signals: int = 0
    sell_signals: int = 0
    wait_signals: int = 0
    avg_confidence: float = 0.0
    confidence_quality: Quality = "NONE"
    execution_rate: float = 0.0
    execution_quality: Quality = "NONE"
    risk_pass_rate: float = 0.0
    risk_quality: Quality = "NONE"
    session_efficiency: float = 0.0
    strategy_score: float = 0.0
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
