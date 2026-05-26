from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from backend.institutional_intelligence.setup_validator_models import SetupValidationContext, SetupValidationResult


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SimulationOrderIntent(BaseModel):
    intent_id: str = Field(default_factory=lambda: f"SIM-{uuid4().hex}")
    symbol: str
    timeframe: str
    direction: Literal["BUY", "SELL", "NONE"] = "NONE"
    entry_low: float | None = None
    entry_high: float | None = None
    invalidation_level: float | None = None
    target_level: float | None = None
    estimated_rr: float = Field(default=0.0, ge=0.0)
    risk_quality: Literal["EXCELLENT", "GOOD", "ACCEPTABLE", "POOR", "INVALID"] = "INVALID"
    source_model_id: str | None = None
    source_validation_id: str | None = None
    simulation_only: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class InstitutionalSimulationDecision(BaseModel):
    decision_id: str = Field(default_factory=lambda: f"DEC-{uuid4().hex}")
    symbol: str
    timeframe: str
    action: Literal["SIMULATE_BUY", "SIMULATE_SELL", "WAIT", "AVOID", "NO_TRADE"] = "NO_TRADE"
    approved_for_simulation: bool = False
    readiness: Literal[
        "APPROVED_FOR_SIMULATION",
        "WAIT_FOR_CONFIRMATION",
        "BLOCKED",
        "NO_VALID_SETUP",
    ] = "NO_VALID_SETUP"
    confidence: float = Field(default=0.0, ge=0.0, le=100.0)
    setup_quality: str = "REJECTED"
    selected_model_type: str | None = None
    order_intent: SimulationOrderIntent
    approval_reasons: list[str] = Field(default_factory=list)
    rejection_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    explanation: str = ""
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)


class SimulationDecisionContext(BaseModel):
    symbol: str
    timeframe: str
    validation_context: SetupValidationContext
    selected_validation: SetupValidationResult | None = None
    decision: InstitutionalSimulationDecision
    timestamp: datetime = Field(default_factory=utc_now)
