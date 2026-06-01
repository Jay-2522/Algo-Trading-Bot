from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


ServiceStatus = Literal["RUNNING", "STOPPED", "DEGRADED", "UNKNOWN"]
RuntimeStatus = Literal["READY_FOR_LOCAL_RUNTIME", "READY_FOR_VPS_RUNTIME", "WARNING", "BLOCKED"]


class RuntimeServiceStatus(BaseModel):
    service_name: str
    running: bool = False
    port: int | None = None
    health_endpoint: str | None = None
    last_health_check: datetime = Field(default_factory=utc_now)
    status: ServiceStatus = "UNKNOWN"
    warnings: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)


class VPSRuntimeStatus(BaseModel):
    status: RuntimeStatus = "WARNING"
    backend_service: RuntimeServiceStatus
    frontend_service: RuntimeServiceStatus
    mt5_terminal_required: bool = True
    runtime_ready: bool = False
    service_management_ready: bool = False
    healthcheck_ready: bool = False
    warnings: list[str] = Field(default_factory=list)
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
