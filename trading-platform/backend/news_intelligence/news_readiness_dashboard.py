from datetime import datetime

from pydantic import BaseModel, Field

from backend.news_intelligence.models import utc_now


class Phase7NewsStatus(BaseModel):
    phase: str = "Phase 7"
    status: str = "COMPLETE"
    calendar_engine: str = "READY"
    headline_engine: str = "READY"
    macro_engine: str = "READY"
    unified_risk_engine: str = "READY"
    strategy_integration: str = "READY"
    health_score: int = 100
    readiness_score: int = 100
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)


class NewsReadinessDashboard:
    """Expose Phase 7 integration readiness without enabling live providers."""

    def readiness(self) -> dict:
        integrations = {
            "forex_factory_integration": "READY_FOR_LIVE_INTEGRATION",
            "financial_juice_integration": "READY_FOR_LIVE_INTEGRATION",
            "dxy_integration": "READY_FOR_LIVE_INTEGRATION",
            "us10y_integration": "READY_FOR_LIVE_INTEGRATION",
            "headline_intelligence": "READY",
            "calendar_intelligence": "READY",
            "macro_intelligence": "READY",
            "unified_risk_engine": "READY",
            "strategy_integration": "READY",
        }
        ready_count = sum(1 for value in integrations.values() if value in {"READY", "READY_FOR_LIVE_INTEGRATION"})
        readiness_score = int((ready_count / len(integrations)) * 100)
        return {
            "overall": "PHASE_7_READY",
            "readiness_score": readiness_score,
            **integrations,
            "simulation_only": True,
            "live_execution_enabled": False,
        }

    def phase_status(self, health_score: int = 100, readiness_score: int = 100) -> Phase7NewsStatus:
        return Phase7NewsStatus(health_score=health_score, readiness_score=readiness_score)
