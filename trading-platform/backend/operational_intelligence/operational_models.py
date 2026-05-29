from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OperationalHealthSummary(BaseModel):
    overall_status: Literal["HEALTHY", "WARNING", "DEGRADED", "CRITICAL"]
    health_score: int
    active_warnings: int
    active_alerts: int
    monitored_modules: int
    simulation_only: bool = True
    live_execution_enabled: bool = False


class OperationalModuleStatus(BaseModel):
    module_name: str
    status: Literal["HEALTHY", "WARNING", "FAILED", "DISABLED"]
    last_check: datetime = Field(default_factory=utc_now)
    message: str


class WarningSummary(BaseModel):
    warning_id: str = Field(default_factory=lambda: f"op_warning_{uuid4().hex[:12]}")
    category: str
    severity: Literal["INFO", "WARNING", "ERROR", "CRITICAL"]
    message: str
    timestamp: datetime = Field(default_factory=utc_now)
