from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


ReadinessState = Literal["READY", "WARNING", "PENDING", "PENDING_IMPLEMENTATION", "FOUNDATION_READY"]


class ExecutiveDashboardSummary(BaseModel):
    analytics_ready: bool = True
    reports_ready: bool = True
    accounts_ready: bool = True
    copier_ready: bool = True
    strategy_ready: bool = True
    deployment_ready: bool = True
    monitoring_ready: bool = True
    security_ready: bool = True
    production_ready: bool = False
    xauusd_ready: bool = True
    eurusd_ready: bool = True
    nifty50_ready: bool = False
    overall_completion_percentage: float = 88.0
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
        self.overall_completion_percentage = min(float(self.overall_completion_percentage), 92.0)


class ReadinessItem(BaseModel):
    name: str
    status: ReadinessState
    score: float
    reason: str


class InstrumentReadiness(BaseModel):
    symbol: str
    status: ReadinessState
    ready: bool
    reason: str


class ExecutiveSystemHealth(BaseModel):
    deployment_score: float
    monitoring_score: float
    security_score: float
    production_score: float
    simulation_only: bool = True
    live_execution_enabled: bool = False
    broker_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)
