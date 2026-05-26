from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


DashboardStatus = Literal["ACTIVE", "WAITING", "BLOCKED", "HEALTHY", "WARNING", "CRITICAL", "INACTIVE"]
DashboardSeverity = Literal["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
DashboardAction = Literal[
    "MONITOR",
    "WAIT",
    "AVOID",
    "READY_FOR_SIMULATION",
    "MANAGE_POSITION",
    "REVIEW_SYSTEM",
]


class DashboardCard(BaseModel):
    card_id: str = Field(default_factory=lambda: f"DSH-{uuid4().hex}")
    title: str
    status: DashboardStatus = "INACTIVE"
    value: Any = None
    subtitle: str = ""
    severity: DashboardSeverity = "INFO"
    data: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)


class DashboardAlert(BaseModel):
    alert_id: str = Field(default_factory=lambda: f"ALT-{uuid4().hex}")
    severity: DashboardSeverity = "INFO"
    category: str
    message: str
    recommended_action: str
    timestamp: datetime = Field(default_factory=utc_now)


class DashboardRecommendation(BaseModel):
    action: DashboardAction = "MONITOR"
    confidence: float = Field(default=0.0, ge=0.0, le=100.0)
    reason: str = ""
    next_step: str = ""
    simulation_allowed: bool = False


class InstitutionalDashboardContext(BaseModel):
    symbol: str
    timeframe: str
    cards: list[DashboardCard] = Field(default_factory=list)
    market_overview: DashboardCard
    institutional_bias: DashboardCard
    confluence: DashboardCard
    alignment: DashboardCard
    session: DashboardCard
    entry_model: DashboardCard
    setup_validation: DashboardCard
    simulation_decision: DashboardCard
    paper_trade: DashboardCard
    position_management: DashboardCard
    performance: DashboardCard
    reasoning: DashboardCard
    alerts: list[DashboardAlert] = Field(default_factory=list)
    final_recommendation: DashboardRecommendation
    dashboard_status: DashboardStatus = "INACTIVE"
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)
