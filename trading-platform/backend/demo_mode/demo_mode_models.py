from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ExecutiveKPI(BaseModel):
    label: str
    value: str
    status: Literal["READY", "ACTIVE", "DISABLED", "CONDITIONAL", "PLANNED"]
    description: str


class ClientDemoOverview(BaseModel):
    system_status: str
    client_mvp_status: str
    supported_markets: list[str]
    supported_brokers: list[str]
    pipeline_summary: list[str]
    safety_summary: list[str]
    kpis: list[ExecutiveKPI]
    next_steps: list[str]
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)
