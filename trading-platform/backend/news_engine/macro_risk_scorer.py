from backend.news_engine.blackout_window import BlackoutWindowService
from backend.news_engine.news_models import EconomicEvent, MacroRiskScore


class MacroRiskScorer:
    """Calculate macro risk from scheduled-event severity and blackout state."""

    def __init__(self, blackout_service: BlackoutWindowService | None = None) -> None:
        self.blackout_service = blackout_service or BlackoutWindowService()

    def calculate_macro_risk(self, events: list[EconomicEvent]) -> MacroRiskScore:
        active_blackout = self.blackout_service.is_in_blackout_window(events)
        high_events = sum(event.impact == "HIGH" for event in events)
        medium_events = sum(event.impact == "MEDIUM" for event in events)

        if active_blackout:
            event_score, risk_level = 100.0, "BLOCKED"
        elif high_events:
            event_score, risk_level = min(75 + high_events * 5, 95), "HIGH"
        elif medium_events >= 2:
            event_score, risk_level = 65.0, "MEDIUM"
        elif medium_events:
            event_score, risk_level = 45.0, "MEDIUM"
        else:
            event_score, risk_level = 10.0, "LOW"

        volatility_score = min(100.0, event_score * 0.8)
        dxy_score = 50.0
        bond_yield_score = 50.0
        overall = round(
            event_score * 0.5
            + volatility_score * 0.2
            + dxy_score * 0.15
            + bond_yield_score * 0.15,
            2,
        )
        return MacroRiskScore(
            event_risk_score=event_score,
            volatility_risk_score=volatility_score,
            dxy_risk_score=dxy_score,
            bond_yield_risk_score=bond_yield_score,
            overall_macro_score=overall,
            risk_level=risk_level,
        )

