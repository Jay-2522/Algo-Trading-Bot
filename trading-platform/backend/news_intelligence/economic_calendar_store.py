from datetime import datetime, timedelta, timezone

from backend.news_intelligence.models import EconomicCalendarEvent


class EconomicCalendarStore:
    """In-memory economic calendar store for manual ingestion fixtures."""

    _events: dict[str, EconomicCalendarEvent] = {}

    def upsert_events(self, events: list[EconomicCalendarEvent]) -> list[EconomicCalendarEvent]:
        for event in events:
            self._events[event.event_id] = event
        return events

    def list_events(self, limit: int = 100) -> list[EconomicCalendarEvent]:
        events = sorted(
            self._events.values(),
            key=lambda event: event.scheduled_time or datetime.max.replace(tzinfo=timezone.utc),
        )
        return events[:limit]

    def upcoming_events(
        self,
        now_utc: datetime | None = None,
        window_hours: int = 24,
    ) -> list[EconomicCalendarEvent]:
        now = now_utc or datetime.now(timezone.utc)
        end = now + timedelta(hours=window_hours)
        return [
            event
            for event in self.list_events()
            if event.scheduled_time is not None and now <= event.scheduled_time <= end
        ]

    def active_risk_events(self, now_utc: datetime | None = None) -> list[EconomicCalendarEvent]:
        return [event for event in self.list_events() if event.active_risk_window]

    def clear(self) -> None:
        self._events.clear()
