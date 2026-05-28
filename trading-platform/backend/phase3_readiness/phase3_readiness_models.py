from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Phase3ModuleStatus(BaseModel):
    module_name: str
    route_available: bool = False
    status: str = "NOT_CHECKED"
    simulation_only: bool = True
    live_execution_enabled: bool = False
    message: str = ""


class Phase3ReadinessReport(BaseModel):
    phase: str = "Phase 3"
    overall_status: Literal["READY", "WARNING", "INCOMPLETE", "FAILED"] = "INCOMPLETE"
    completed_modules: list[str] = Field(default_factory=list)
    missing_modules: list[str] = Field(default_factory=list)
    warning_modules: list[str] = Field(default_factory=list)
    total_routes: int = 0
    safety_status: str = "UNKNOWN"
    client_mvp_status: str = "UNKNOWN"
    next_phase: str = "Phase 4 VPS dashboard and demo execution preparation"
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)


class Phase3PipelineValidation(BaseModel):
    webhook_ready: bool = False
    routing_ready: bool = False
    allocation_ready: bool = False
    execution_queue_ready: bool = False
    simulation_lifecycle_ready: bool = False
    monitoring_ready: bool = False
    pipeline_status: str = "NOT_VALIDATED"
    issues: list[str] = Field(default_factory=list)
    simulation_only: bool = True
    live_execution_enabled: bool = False


class Phase3SafetyAudit(BaseModel):
    no_order_send_detected: bool = False
    live_execution_disabled: bool = True
    broker_execution_disabled: bool = True
    simulation_only_confirmed: bool = True
    safety_status: str = "UNKNOWN"
    warnings: list[str] = Field(default_factory=list)
