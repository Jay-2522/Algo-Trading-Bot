from backend.news_intelligence.models import NewsEvent


class NewsRiskEngine:
    """Evaluate placeholder macro-event risk for future strategy filters."""

    def evaluate(self, event: NewsEvent) -> NewsEvent:
        category = event.category.upper()
        if category in {"FOMC", "NFP"}:
            event.risk_level = "EXTREME"
        elif category in {"CPI", "PPI", "GDP"}:
            event.risk_level = "HIGH"
        elif category == "PMI":
            event.risk_level = "MEDIUM"
        elif event.impact == "LOW":
            event.risk_level = "LOW"
        elif event.impact == "MEDIUM":
            event.risk_level = "MEDIUM"
        else:
            event.risk_level = "HIGH"
        return event
