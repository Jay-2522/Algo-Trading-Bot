from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DashboardCard(BaseModel):
    card_id: str
    title: str
    status: str
    value: str
    subtitle: str
    severity: Literal["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"] = "INFO"
    metadata: dict[str, Any] = Field(default_factory=dict)
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)


class DashboardOverview(BaseModel):
    overall_status: str
    system_status: dict[str, Any] = Field(default_factory=dict)
    broker_status: dict[str, Any] = Field(default_factory=dict)
    webhook_status: dict[str, Any] = Field(default_factory=dict)
    execution_status: dict[str, Any] = Field(default_factory=dict)
    monitoring_status: dict[str, Any] = Field(default_factory=dict)
    phase3_status: dict[str, Any] = Field(default_factory=dict)
    cards: list[DashboardCard] = Field(default_factory=list)
    alerts: list[dict[str, Any]] = Field(default_factory=list)
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)


class DashboardStatusResponse(BaseModel):
    status: str
    mode: str = "VPS_DASHBOARD_BACKEND_CONTEXT_ONLY"
    dashboard_ready: bool
    platform_health_score: int = 0
    system_status: str = "UNKNOWN"
    phase3_status: str = "UNKNOWN"
    metric_sources: list[dict[str, Any]] = Field(default_factory=list)
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)
