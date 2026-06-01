from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


BackupStatus = Literal["READY", "WARNING", "BLOCKED"]


class BackupReadinessStatus(BaseModel):
    status: BackupStatus = "WARNING"
    backups_defined: bool = False
    rollback_defined: bool = False
    recovery_defined: bool = False
    incident_response_defined: bool = False
    recovery_score: int = 0
    warnings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
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
