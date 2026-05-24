from datetime import datetime, timezone
from typing import Any, Dict

from pydantic import BaseModel, Field


class BaseStrategySignal(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    symbol: str
    timeframe: str
    confidence: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TrendSignal(BaseStrategySignal):
    trend: str
    ema_50: float | None = None
    ema_200: float | None = None


class LiquiditySignal(BaseStrategySignal):
    liquidity_zones: Dict[str, Any] = Field(default_factory=dict)


class StructureSignal(BaseStrategySignal):
    structure: Dict[str, Any] = Field(default_factory=dict)


class StrategySnapshot(BaseStrategySignal):
    trend_analysis: Dict[str, Any]
    liquidity_analysis: Dict[str, Any]
    structure_analysis: Dict[str, Any]
    session_info: Dict[str, Any]
    status: str = "analysis_ready"

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")

