from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ReplayBlockReasonMetrics(BaseModel):
    total_blocked: int = Field(default=0, ge=0)
    block_rate: float = Field(default=0.0, ge=0.0, le=100.0)
    common_reasons: list[str] = Field(default_factory=list)
    gate_counts: dict[str, int] = Field(default_factory=dict)
    most_restrictive_gate: str = "NONE"


class ThresholdAdjustmentSuggestion(BaseModel):
    threshold_name: str
    current_value: float | str
    suggested_value: float | str
    adjustment_direction: Literal["RELAX", "TIGHTEN", "KEEP"]
    confidence: float = Field(default=0.0, ge=0.0, le=100.0)
    reason: str
    safety_note: str


class ReplayCalibrationReport(BaseModel):
    replay_id: str
    symbol: str
    timeframe: str
    block_reason_metrics: ReplayBlockReasonMetrics
    threshold_suggestions: list[ThresholdAdjustmentSuggestion] = Field(default_factory=list)
    calibration_status: Literal["HEALTHY", "TOO_RESTRICTIVE", "TOO_LOOSE", "INSUFFICIENT_DATA"]
    summary: str
    warnings: list[str] = Field(default_factory=list)
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)
