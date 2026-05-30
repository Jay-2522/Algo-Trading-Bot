from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from backend.news_intelligence.models import utc_now


MacroDirection = Literal["UP", "DOWN", "FLAT", "UNKNOWN"]
MacroMomentum = Literal["STRONG", "MODERATE", "WEAK", "UNKNOWN"]
GoldBias = Literal["BULLISH", "BEARISH", "MIXED", "UNKNOWN"]
MacroAlignment = Literal["ALIGNED", "CONFLICTING", "NEUTRAL", "UNKNOWN"]
MacroRiskLevel = Literal["LOW", "MEDIUM", "HIGH"]


class MacroInstrumentContext(BaseModel):
    symbol: str
    current_value: float | None = None
    previous_value: float | None = None
    change: float | None = None
    change_percent: float | None = None
    direction: MacroDirection = "UNKNOWN"
    momentum: MacroMomentum = "UNKNOWN"
    confidence: float = 0.0
    timestamp: datetime = Field(default_factory=utc_now)


class XAUUSDMacroBiasContext(BaseModel):
    dxy_context: MacroInstrumentContext | None = None
    us10y_context: MacroInstrumentContext | None = None
    gold_bias: GoldBias = "UNKNOWN"
    macro_alignment: MacroAlignment = "UNKNOWN"
    macro_risk_level: MacroRiskLevel = "MEDIUM"
    confidence_adjustment: float = 0.0
    reason: str = "Macro context is unavailable."
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)
