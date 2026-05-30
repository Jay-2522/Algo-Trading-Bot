from datetime import datetime, timedelta, timezone
from uuid import uuid4

from backend.news_intelligence.event_classifier import EventClassifier
from backend.news_intelligence.models import NewsEvent, NewsIntelligenceStatus
from backend.news_intelligence.news_risk_engine import NewsRiskEngine


class NewsService:
    """Architecture-only news intelligence service with placeholder calendar data."""

    SUPPORTED_SOURCES = ["FOREX_FACTORY_PENDING", "FINANCIAL_JUICE_PENDING", "DXY_PENDING", "US10Y_PENDING"]

    def __init__(
        self,
        classifier: EventClassifier | None = None,
        risk_engine: NewsRiskEngine | None = None,
    ) -> None:
        self.classifier = classifier or EventClassifier()
        self.risk_engine = risk_engine or NewsRiskEngine()

    def get_status(self) -> NewsIntelligenceStatus:
        return NewsIntelligenceStatus(
            status="ARCHITECTURE_READY",
            architecture_ready=True,
            sources_supported=self.get_supported_sources(),
            event_types_supported=self.get_supported_events(),
            risk_engine_ready=True,
            strategy_integration_ready=True,
            simulation_only=True,
            live_execution_enabled=False,
        )

    def get_supported_sources(self) -> list[str]:
        return list(self.SUPPORTED_SOURCES)

    def get_supported_events(self) -> list[str]:
        return list(self.classifier.SUPPORTED_CATEGORIES)

    def build_placeholder_calendar(self) -> list[NewsEvent]:
        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        titles = [
            ("US CPI Placeholder", "USD", "FOREX_FACTORY_PENDING", 6),
            ("US Non-Farm Payrolls Placeholder", "USD", "FOREX_FACTORY_PENDING", 30),
            ("FOMC Rate Decision Placeholder", "USD", "FINANCIAL_JUICE_PENDING", 45),
            ("US PMI Placeholder", "USD", "FOREX_FACTORY_PENDING", 12),
        ]
        events: list[NewsEvent] = []
        for title, currency, source, hours_ahead in titles:
            category, impact = self.classifier.classify(title)
            event = NewsEvent(
                event_id=f"news-{uuid4().hex}",
                title=title,
                category=category,
                currency=currency,
                impact=impact,
                scheduled_time=now + timedelta(hours=hours_ahead),
                source=source,
                risk_level="LOW",
                active=False,
                warnings=["Placeholder only; no external API, API key, or scraping is active."],
            )
            events.append(self.risk_engine.evaluate(event))
        return events
