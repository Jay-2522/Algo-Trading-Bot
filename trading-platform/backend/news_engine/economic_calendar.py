from datetime import datetime, timedelta, timezone

from backend.news_engine.news_models import EconomicEvent


class EconomicCalendarService:
    """Supply dynamic sample events until external calendar feeds are integrated."""

    def get_upcoming_events(self, now: datetime | None = None) -> list[EconomicEvent]:
        anchor = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        return [
            self._event("mock-cpi", "US Consumer Price Index (CPI)", "US", "USD", "HIGH", anchor + timedelta(minutes=10), "CPI"),
            self._event("mock-nfp", "US Nonfarm Payrolls (NFP)", "US", "USD", "HIGH", anchor + timedelta(hours=3), "NFP"),
            self._event("mock-fomc", "FOMC Rate Decision", "US", "USD", "HIGH", anchor + timedelta(days=1), "FOMC"),
            self._event("mock-fed-speech", "Federal Reserve Chair Speech", "US", "USD", "MEDIUM", anchor + timedelta(hours=6), "FED_SPEECH"),
        ]

    def get_high_impact_events(self, now: datetime | None = None) -> list[EconomicEvent]:
        return [event for event in self.get_upcoming_events(now) if event.impact == "HIGH"]

    def get_events_by_currency(self, currency: str, now: datetime | None = None) -> list[EconomicEvent]:
        normalized = currency.strip().upper()
        return [event for event in self.get_upcoming_events(now) if event.currency == normalized]

    def get_events_by_category(self, category: str, now: datetime | None = None) -> list[EconomicEvent]:
        normalized = category.strip().upper()
        return [event for event in self.get_upcoming_events(now) if event.category == normalized]

    def _event(
        self,
        event_id: str,
        title: str,
        country: str,
        currency: str,
        impact: str,
        event_time: datetime,
        category: str,
    ) -> EconomicEvent:
        return EconomicEvent(
            event_id=event_id,
            title=title,
            country=country,
            currency=currency,
            impact=impact,
            event_time_utc=event_time.isoformat(),
            category=category,
            source="MOCK_CALENDAR_FOUNDATION",
        )

