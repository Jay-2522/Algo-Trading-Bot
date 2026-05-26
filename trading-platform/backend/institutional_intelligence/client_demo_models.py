from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ClientDemoSummary(BaseModel):
    symbol: str
    timeframe: str
    phase: str = "PHASE_2"
    system_status: str
    institutional_bias: str
    dashboard_status: str
    recommendation: str
    confidence: float = Field(default=0.0, ge=0.0, le=100.0)
    explanation: str
    key_strengths: list[str] = Field(default_factory=list)
    key_risks: list[str] = Field(default_factory=list)
    safety_status: str
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)


class ClientDemoModule(BaseModel):
    module_name: str
    status: Literal["READY", "WARNING", "FAILED", "NOT_AVAILABLE"]
    purpose: str
    client_value: str


class ClientDemoReport(BaseModel):
    summary: ClientDemoSummary
    modules: list[ClientDemoModule] = Field(default_factory=list)
    demo_talking_points: list[str] = Field(default_factory=list)
    safe_to_demo: bool = False
    timestamp: datetime = Field(default_factory=utc_now)
