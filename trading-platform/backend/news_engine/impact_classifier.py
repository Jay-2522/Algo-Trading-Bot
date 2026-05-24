from backend.news_engine.news_models import EconomicEvent


class ImpactClassifier:
    """Identify events with elevated market and gold sensitivity."""

    GOLD_SENSITIVE_CATEGORIES = {"CPI", "NFP", "FOMC", "FED_SPEECH"}

    def classify_event(self, event: EconomicEvent) -> dict:
        return {
            "event_id": event.event_id,
            "impact": event.impact,
            "high_impact": self.is_high_impact(event),
            "gold_sensitive": self.is_gold_sensitive(event),
        }

    def is_high_impact(self, event: EconomicEvent) -> bool:
        return event.impact == "HIGH"

    def is_gold_sensitive(self, event: EconomicEvent) -> bool:
        title = event.title.upper()
        return (
            (event.currency == "USD" and event.category in self.GOLD_SENSITIVE_CATEGORIES)
            or "BOND YIELD" in title
            or "DXY" in title
        )

