from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SetupValidationRule(BaseModel):
    rule_name: str
    category: Literal["ALIGNMENT", "SESSION", "CONFLUENCE", "RISK", "STRUCTURE", "NEWS"]
    passed: bool
    score: float = Field(default=0.0, ge=0.0, le=100.0)
    severity: Literal["INFO", "WARNING", "CRITICAL"] = "INFO"
    reason: str


class SetupValidationResult(BaseModel):
    validation_id: str = Field(default_factory=lambda: f"VAL-{uuid4().hex}")
    symbol: str
    timeframe: str
    model_type: str
    direction: str
    source_model_id: str | None = None
    entry_zone_low: float | None = None
    entry_zone_high: float | None = None
    invalidation_level: float | None = None
    target_level: float | None = None
    approved_for_simulation: bool = False
    overall_score: float = Field(default=0.0, ge=0.0, le=100.0)
    confidence: float = Field(default=0.0, ge=0.0, le=100.0)
    readiness: Literal["APPROVED", "CONDITIONAL", "WAIT", "REJECTED"] = "WAIT"
    rules: list[SetupValidationRule] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    rejection_reasons: list[str] = Field(default_factory=list)
    approval_reasons: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=utc_now)


class SetupApprovalDecision(BaseModel):
    approved: bool = False
    approval_grade: Literal[
        "INSTITUTIONAL_A_PLUS",
        "INSTITUTIONAL_A",
        "INSTITUTIONAL_B",
        "LOW_QUALITY",
        "REJECTED",
    ] = "REJECTED"
    execution_readiness: Literal["APPROVED", "CONDITIONAL", "WAIT", "REJECTED"] = "REJECTED"
    simulation_eligible: bool = False
    requires_confirmation: bool = True
    institutional_quality: str = "REJECTED"
    explanation: str = ""


class SetupValidationContext(BaseModel):
    symbol: str
    timeframe: str
    validations: list[SetupValidationResult] = Field(default_factory=list)
    decisions: list[SetupApprovalDecision] = Field(default_factory=list)
    approved_setups: list[SetupValidationResult] = Field(default_factory=list)
    waiting_setups: list[SetupValidationResult] = Field(default_factory=list)
    rejected_setups: list[SetupValidationResult] = Field(default_factory=list)
    best_setup: SetupValidationResult | None = None
    best_decision: SetupApprovalDecision | None = None
    simulation_eligible: bool = False
    execution_readiness: Literal["APPROVED", "CONDITIONAL", "WAIT", "REJECTED"] = "REJECTED"
    confidence: float = Field(default=0.0, ge=0.0, le=100.0)
    timestamp: datetime = Field(default_factory=utc_now)
