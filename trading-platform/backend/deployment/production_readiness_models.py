from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


ProductionOverallStatus = Literal["READY_FOR_DEMO_VPS", "READY_FOR_STAGING", "NEEDS_WORK", "BLOCKED"]


class ProductionReadinessReport(BaseModel):
    overall_status: ProductionOverallStatus = "NEEDS_WORK"
    readiness_score: int = 0
    deployment_score: int = 0
    monitoring_score: int = 0
    security_score: int = 0
    backup_score: int = 0
    execution_score: int = 0
    strategy_score: int = 0
    vps_score: int = 0
    strengths: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
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


class GoLiveAssessment(BaseModel):
    assessment_id: str = Field(default_factory=lambda: f"go_live_assessment_{uuid4().hex[:12]}")
    readiness_score: int = 0
    deployment_ready: bool = False
    monitoring_ready: bool = False
    security_ready: bool = False
    backup_ready: bool = False
    execution_ready: bool = False
    strategy_ready: bool = False
    vps_ready: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)
