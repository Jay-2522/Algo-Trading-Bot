from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


DeploymentStatus = Literal["READY_FOR_VPS_PREP", "READY_FOR_DEMO_VPS", "BLOCKED", "WARNING"]


class EnvironmentAuditResult(BaseModel):
    env_file_present: bool = False
    api_base_url_configured: bool = False
    python_path_ok: bool = False
    node_environment: str = "unknown"
    required_variables_present: bool = False
    env_templates_ready: bool = False
    forbidden_live_flags_detected: bool = False
    simulation_only: bool = True
    live_execution_enabled: bool = False
    broker_execution_enabled: bool = False
    warnings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)

    def model_post_init(self, __context: Any) -> None:
        self.simulation_only = True
        self.live_execution_enabled = False
        self.broker_execution_enabled = False


class VPSEnvironmentCheck(BaseModel):
    os_supported: bool = False
    python_available: bool = False
    node_available: bool = False
    ports_available: bool = True
    required_directories_present: bool = False
    startup_scripts_present: bool = False
    docker_scripts_present: bool = False
    recommended_region: str = "Mumbai"
    latency_target_ms: str = "<10ms ideal"
    warnings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)


class MT5EnvironmentCheck(BaseModel):
    mt5_python_package_available: bool = False
    mt5_terminal_detected: bool = False
    demo_account_required: bool = True
    live_account_blocked: bool = True
    autotrading_required_for_demo: bool = True
    mt5_ready_for_demo: bool = False
    warnings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)


class DeploymentReadinessStatus(BaseModel):
    status: DeploymentStatus = "WARNING"
    environment_ready: bool = False
    vps_ready: bool = False
    mt5_environment_ready: bool = False
    logging_ready: bool = False
    health_checks_ready: bool = False
    docker_ready: bool = False
    compose_ready: bool = False
    env_templates_ready: bool = False
    monitoring_ready: bool = False
    runtime_ready: bool = False
    service_management_ready: bool = False
    deployment_score: int = 0
    blockers: list[str] = Field(default_factory=list)
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
