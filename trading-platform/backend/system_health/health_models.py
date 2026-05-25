from datetime import datetime, timezone

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ModuleHealth(BaseModel):
    module_name: str
    status: str
    route_available: bool
    simulation_only: bool
    live_execution_enabled: bool = False
    message: str


class SystemReadiness(BaseModel):
    overall_status: str
    modules: list[ModuleHealth] = Field(default_factory=list)
    safety_passed: bool
    live_execution_enabled: bool = False
    total_routes: int
    timestamp: datetime = Field(default_factory=utc_now)


class SafetyScanResult(BaseModel):
    passed: bool
    forbidden_patterns_found: list[str] = Field(default_factory=list)
    live_execution_enabled: bool = False
    order_send_found: bool = False
    unsafe_files: list[str] = Field(default_factory=list)
    message: str


class RouteAuditResult(BaseModel):
    total_routes: int
    required_routes: list[str] = Field(default_factory=list)
    missing_routes: list[str] = Field(default_factory=list)
    duplicate_paths: list[str] = Field(default_factory=list)
    passed: bool


class PhaseCompletionReport(BaseModel):
    phase: str
    completed_days: list[str] = Field(default_factory=list)
    completed_modules: list[str] = Field(default_factory=list)
    remaining_items: list[str] = Field(default_factory=list)
    safety_status: str
    readiness_status: str
    summary: str
