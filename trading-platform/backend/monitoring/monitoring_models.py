from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SystemHealthSnapshot(BaseModel):
    snapshot_id: str = Field(default_factory=lambda: f"health_{uuid4().hex[:12]}")
    overall_status: Literal["HEALTHY", "WARNING", "DEGRADED", "CRITICAL"] = "HEALTHY"
    active_modules: int = 0
    warning_modules: int = 0
    failed_modules: int = 0
    uptime_seconds: float = 0.0
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)


class ModuleHealthStatus(BaseModel):
    module_name: str
    status: Literal["HEALTHY", "WARNING", "FAILED", "DISABLED"] = "HEALTHY"
    warnings: list[str] = Field(default_factory=list)
    last_check: datetime = Field(default_factory=utc_now)
    healthy: bool = True


class AlertEvent(BaseModel):
    alert_id: str = Field(default_factory=lambda: f"alert_{uuid4().hex[:12]}")
    severity: Literal["INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    source: str
    title: str
    message: str
    acknowledged: bool = False
    timestamp: datetime = Field(default_factory=utc_now)


class ExecutionMonitoringSummary(BaseModel):
    queued_items: int = 0
    simulated_fills: int = 0
    simulated_rejections: int = 0
    failed_safe: int = 0
    cancelled: int = 0
    timestamp: datetime = Field(default_factory=utc_now)


JsonDict = dict[str, Any]
