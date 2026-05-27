from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class WebhookBrokerRoutingPreview(BaseModel):
    canonical_symbol: str
    broker_targets: list[str] = Field(default_factory=list)
    supported_brokers: list[str] = Field(default_factory=list)
    unsupported_brokers: list[str] = Field(default_factory=list)
    broker_symbol_map: dict[str, str | None] = Field(default_factory=dict)
    routing_ready: bool = False
    message: str = ""


class WebhookInstitutionalContextCheck(BaseModel):
    canonical_symbol: str
    institutional_bias: str = "UNKNOWN"
    dashboard_status: str = "UNKNOWN"
    recommendation: str = "MONITOR"
    confidence: float | None = None
    aligned_with_signal: bool | None = None
    issues: list[str] = Field(default_factory=list)


class WebhookRiskGateResult(BaseModel):
    passed: bool = False
    risk_level: str = "UNKNOWN"
    reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class WebhookOrchestrationDecision(BaseModel):
    decision_id: str = Field(default_factory=lambda: f"webhook_decision_{uuid4().hex[:12]}")
    signal_id: str
    canonical_symbol: str
    action: str
    institutional_status: WebhookInstitutionalContextCheck
    risk_status: WebhookRiskGateResult
    routing_status: WebhookBrokerRoutingPreview
    final_decision: Literal[
        "SIMULATION_ACCEPTED",
        "WAIT_FOR_CONFIRMATION",
        "REJECTED",
        "BLOCKED",
        "INVALID",
    ] = "INVALID"
    broker_targets: list[str] = Field(default_factory=list)
    rejection_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    explanation: str = ""
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)
