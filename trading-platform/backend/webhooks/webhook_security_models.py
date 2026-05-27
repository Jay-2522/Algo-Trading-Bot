from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class WebhookSecurityEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"webhook_sec_{uuid4().hex[:12]}")
    source_ip: str = "unknown"
    fingerprint: str | None = None
    event_type: Literal[
        "DUPLICATE_SIGNAL",
        "REPLAY_ATTACK",
        "RATE_LIMIT",
        "INVALID_PAYLOAD",
        "AUTH_FAILURE",
        "SUSPICIOUS_ACTIVITY",
        "SAFE_REQUEST",
    ] = "SAFE_REQUEST"
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "LOW"
    blocked: bool = False
    reasons: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)


class WebhookReplayProtectionResult(BaseModel):
    allowed: bool = True
    duplicate_detected: bool = False
    replay_detected: bool = False
    fingerprint: str
    reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class WebhookRateLimitResult(BaseModel):
    allowed: bool = True
    request_count: int = 0
    limit: int = 0
    blocked: bool = False
    reset_window_seconds: int = 0
    warnings: list[str] = Field(default_factory=list)
