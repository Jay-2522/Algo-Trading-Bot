from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


SecurityStatus = Literal["READY", "WARNING", "BLOCKED"]
AccessMode = Literal["LOCAL_DEV", "DEMO_VPS", "PRODUCTION_LOCKED"]


class SecretsAuditResult(BaseModel):
    env_files_checked: list[str] = Field(default_factory=list)
    required_secret_placeholders_present: bool = False
    real_secrets_detected_in_repo: bool = False
    missing_secret_placeholders: list[str] = Field(default_factory=list)
    unsafe_live_flags: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)


class AccessPolicyStatus(BaseModel):
    mode: AccessMode = "LOCAL_DEV"
    admin_routes_protected: bool = False
    client_routes_public_safe: bool = True
    operations_routes_restricted_placeholder: bool = True
    api_key_guard_ready: bool = True
    warnings: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)


class SecurityReadinessStatus(BaseModel):
    status: SecurityStatus = "WARNING"
    security_score: int = 0
    secrets_ready: bool = False
    access_policy_ready: bool = False
    cors_policy_ready: bool = False
    unsafe_flags_detected: bool = False
    redaction_ready: bool = False
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
