from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Phase2ModuleStatus(BaseModel):
    module_name: str
    route_available: bool = False
    status: Literal["READY", "WARNING", "FAILED", "NOT_AVAILABLE"] = "NOT_AVAILABLE"
    simulation_only: bool = True
    live_execution_enabled: bool = False
    message: str = ""


class Phase2SafetyAudit(BaseModel):
    passed: bool = False
    simulation_only: bool = True
    live_execution_enabled: bool = False
    order_send_found: bool = False
    unsafe_patterns: list[str] = Field(default_factory=list)
    message: str = ""


class Phase2ReadinessReport(BaseModel):
    phase: str = "PHASE_2"
    overall_status: Literal["READY", "WARNING", "FAILED"] = "WARNING"
    completed_modules: list[str] = Field(default_factory=list)
    module_statuses: list[Phase2ModuleStatus] = Field(default_factory=list)
    total_routes: int = Field(default=0, ge=0)
    institutional_routes: list[str] = Field(default_factory=list)
    missing_routes: list[str] = Field(default_factory=list)
    safety_audit: Phase2SafetyAudit
    dashboard_ready: bool = False
    reasoning_ready: bool = False
    orchestration_ready: bool = False
    performance_ready: bool = False
    simulation_only: bool = True
    live_execution_enabled: bool = False
    summary: str = ""
    safety_summary: str = ""
    client_ready_summary: str = ""
    next_phase_direction: str = ""
    timestamp: datetime = Field(default_factory=utc_now)
