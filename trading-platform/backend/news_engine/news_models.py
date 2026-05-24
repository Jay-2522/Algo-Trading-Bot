from pydantic import BaseModel, Field


class EconomicEvent(BaseModel):
    """Normalized economic-calendar event for macro-risk evaluation."""

    event_id: str
    title: str
    country: str
    currency: str
    impact: str
    event_time_utc: str
    category: str
    source: str | None = None


class NewsRiskStatus(BaseModel):
    trading_allowed: bool
    risk_level: str
    active_blackout: bool
    reason: str
    upcoming_events: list[EconomicEvent] = Field(default_factory=list)
    timestamp: str


class BlackoutWindow(BaseModel):
    event_id: str
    title: str
    start_time_utc: str
    end_time_utc: str
    reason: str


class MacroRiskScore(BaseModel):
    event_risk_score: float = Field(ge=0, le=100)
    volatility_risk_score: float = Field(ge=0, le=100)
    dxy_risk_score: float = Field(ge=0, le=100)
    bond_yield_risk_score: float = Field(ge=0, le=100)
    overall_macro_score: float = Field(ge=0, le=100)
    risk_level: str

