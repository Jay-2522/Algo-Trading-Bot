from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

from backend.institutional_intelligence.breaker_block_models import BreakerBlockContext
from backend.institutional_intelligence.confluence_models import ConfluenceContext
from backend.institutional_intelligence.entry_model_models import EntryModelContext
from backend.institutional_intelligence.fair_value_gap_models import FVGContext
from backend.institutional_intelligence.liquidity_sweep_models import SweepContext
from backend.institutional_intelligence.multi_timeframe_models import MultiTimeframeAlignment
from backend.institutional_intelligence.order_block_models import OrderBlockContext
from backend.institutional_intelligence.paper_trade_models import PaperTradeLifecycleContext
from backend.institutional_intelligence.position_management_models import InstitutionalPositionManagement
from backend.institutional_intelligence.session_models import SessionIntelligenceContext
from backend.institutional_intelligence.setup_validator_models import SetupValidationContext
from backend.institutional_intelligence.simulation_decision_models import SimulationDecisionContext
from backend.institutional_intelligence.smc_models import InstitutionalContext
from backend.institutional_intelligence.structure_shift_models import StructureShiftContext


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class InstitutionalPipelineStep(BaseModel):
    step_name: str
    status: Literal["PASSED", "WARNING", "FAILED", "SKIPPED"]
    success: bool = False
    duration_ms: float = Field(default=0.0, ge=0.0)
    error: str | None = None
    summary: str = ""


class InstitutionalSystemState(BaseModel):
    symbol: str
    timeframe: str
    market_state: str = "UNCLEAR"
    institutional_bias: str = "UNCLEAR"
    setup_state: str = "NO_SETUP"
    simulation_state: str = "NO_VALID_SETUP"
    position_state: str = "NO_POSITION"
    risk_state: str = "SAFE"
    final_state: Literal[
        "READY_FOR_SIMULATION",
        "WAITING_FOR_CONFIRMATION",
        "NO_TRADE",
        "BLOCKED",
        "MANAGING_POSITION",
        "ERROR_SAFE_MODE",
    ] = "NO_TRADE"
    confidence: float = Field(default=0.0, ge=0.0, le=100.0)
    warnings: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)


class InstitutionalOrchestrationReport(BaseModel):
    symbol: str
    timeframe: str
    pipeline_steps: list[InstitutionalPipelineStep] = Field(default_factory=list)
    institutional_context: InstitutionalContext | None = None
    sweep_context: SweepContext | None = None
    fvg_context: FVGContext | None = None
    order_block_context: OrderBlockContext | None = None
    breaker_context: BreakerBlockContext | None = None
    structure_shift_context: StructureShiftContext | None = None
    confluence_context: ConfluenceContext | None = None
    alignment_context: MultiTimeframeAlignment | None = None
    session_context: SessionIntelligenceContext | None = None
    entry_model_context: EntryModelContext | None = None
    setup_validation_context: SetupValidationContext | None = None
    simulation_decision_context: SimulationDecisionContext | None = None
    paper_trade_context: PaperTradeLifecycleContext | None = None
    position_management_context: InstitutionalPositionManagement | None = None
    system_state: InstitutionalSystemState | None = None
    executive_summary: str = ""
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)


class InstitutionalHealthResult(BaseModel):
    status: Literal["HEALTHY", "DEGRADED", "SAFE_MODE"]
    passed: bool
    available_steps: int = Field(default=0, ge=0)
    failed_steps: list[str] = Field(default_factory=list)
    simulation_only: bool = True
    live_execution_enabled: bool = False
    json_safe: bool = True
    route_ready: bool = True
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
