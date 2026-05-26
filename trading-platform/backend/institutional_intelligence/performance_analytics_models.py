from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SetupPerformanceMetrics(BaseModel):
    total_setups: int = Field(default=0, ge=0)
    approved_setups: int = Field(default=0, ge=0)
    rejected_setups: int = Field(default=0, ge=0)
    waiting_setups: int = Field(default=0, ge=0)
    approval_rate: float = Field(default=0.0, ge=0.0, le=100.0)
    rejection_rate: float = Field(default=0.0, ge=0.0, le=100.0)
    average_setup_score: float = Field(default=0.0, ge=0.0, le=100.0)
    best_setup_type: str | None = None
    weakest_setup_type: str | None = None
    recurring_rejection_reasons: list[str] = Field(default_factory=list)


class DecisionQualityMetrics(BaseModel):
    total_decisions: int = Field(default=0, ge=0)
    simulate_buy_count: int = Field(default=0, ge=0)
    simulate_sell_count: int = Field(default=0, ge=0)
    wait_count: int = Field(default=0, ge=0)
    avoid_count: int = Field(default=0, ge=0)
    no_trade_count: int = Field(default=0, ge=0)
    decision_block_rate: float = Field(default=0.0, ge=0.0, le=100.0)
    average_confidence: float = Field(default=0.0, ge=0.0, le=100.0)
    most_common_action: str | None = None
    recurring_block_reasons: list[str] = Field(default_factory=list)


class PaperTradePerformanceMetrics(BaseModel):
    total_candidates: int = Field(default=0, ge=0)
    activated_positions: int = Field(default=0, ge=0)
    closed_positions: int = Field(default=0, ge=0)
    win_count: int = Field(default=0, ge=0)
    loss_count: int = Field(default=0, ge=0)
    breakeven_count: int = Field(default=0, ge=0)
    win_rate: float = Field(default=0.0, ge=0.0, le=100.0)
    average_rr: float = 0.0
    average_pnl_points: float = 0.0
    best_trade_rr: float = 0.0
    worst_trade_rr: float = 0.0


class PositionManagementMetrics(BaseModel):
    partial_tp_count: int = Field(default=0, ge=0)
    break_even_moves: int = Field(default=0, ge=0)
    trailing_adjustments: int = Field(default=0, ge=0)
    structural_exits: int = Field(default=0, ge=0)
    emergency_exits: int = Field(default=0, ge=0)
    average_management_quality: float = Field(default=0.0, ge=0.0, le=100.0)
    most_common_exit_reason: str | None = None


class InstitutionalOptimizationRecommendation(BaseModel):
    recommendation_id: str = Field(default_factory=lambda: f"OPT-{uuid4().hex}")
    category: Literal[
        "SETUP_QUALITY",
        "CONFLUENCE",
        "SESSION_TIMING",
        "RISK",
        "STRUCTURE",
        "POSITION_MANAGEMENT",
        "DATA_QUALITY",
    ]
    severity: Literal["INFO", "WARNING", "CRITICAL"]
    title: str
    description: str
    suggested_action: str
    expected_impact: str


class InstitutionalPerformanceAnalyticsContext(BaseModel):
    symbol: str
    timeframe: str
    setup_metrics: SetupPerformanceMetrics = Field(default_factory=SetupPerformanceMetrics)
    decision_metrics: DecisionQualityMetrics = Field(default_factory=DecisionQualityMetrics)
    paper_trade_metrics: PaperTradePerformanceMetrics = Field(default_factory=PaperTradePerformanceMetrics)
    position_management_metrics: PositionManagementMetrics = Field(default_factory=PositionManagementMetrics)
    recommendations: list[InstitutionalOptimizationRecommendation] = Field(default_factory=list)
    overall_health_score: float = Field(default=0.0, ge=0.0, le=100.0)
    optimization_status: Literal["HEALTHY", "NEEDS_ATTENTION", "DEGRADED", "INSUFFICIENT_DATA"] = "INSUFFICIENT_DATA"
    summary: str = ""
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)
