from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


ControlActionType = Literal[
    "PAUSE_QUEUE",
    "RESUME_QUEUE",
    "CANCEL_QUEUE_ITEM",
    "ACKNOWLEDGE_ALERT",
    "EMERGENCY_STOP_PLACEHOLDER",
    "SAFETY_STATUS_CHECK",
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SafetyControlState(BaseModel):
    queue_paused: bool = False
    emergency_stop_active: bool = False
    live_execution_enabled: bool = False
    broker_execution_enabled: bool = False
    simulation_only: bool = True
    active_locks: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)


class ManualOverrideAction(BaseModel):
    action_id: str = Field(default_factory=lambda: f"manual_action_{uuid4().hex[:12]}")
    action_type: ControlActionType
    reason: str
    performed_by: str = "dashboard_operator"
    accepted: bool
    message: str
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)


class ControlAuditEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"control_audit_{uuid4().hex[:12]}")
    action_type: ControlActionType
    reason: str
    result: dict[str, Any]
    timestamp: datetime = Field(default_factory=utc_now)
