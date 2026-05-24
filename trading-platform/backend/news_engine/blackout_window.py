from datetime import datetime, timedelta, timezone

from backend.news_engine.news_models import BlackoutWindow, EconomicEvent


class BlackoutWindowService:
    """Create and evaluate high-impact macro no-trade blackout windows."""

    def create_blackout_window(self, event: EconomicEvent) -> BlackoutWindow | None:
        if event.impact != "HIGH":
            return None
        event_time = datetime.fromisoformat(event.event_time_utc)
        return BlackoutWindow(
            event_id=event.event_id,
            title=event.title,
            start_time_utc=(event_time - timedelta(minutes=30)).isoformat(),
            end_time_utc=(event_time + timedelta(minutes=30)).isoformat(),
            reason="High-impact economic event blackout: trading paused 30 minutes before and after release.",
        )

    def get_active_blackouts(
        self,
        events: list[EconomicEvent],
        now: datetime | None = None,
    ) -> list[BlackoutWindow]:
        current_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        active: list[BlackoutWindow] = []
        for event in events:
            window = self.create_blackout_window(event)
            if window is None:
                continue
            start = datetime.fromisoformat(window.start_time_utc)
            end = datetime.fromisoformat(window.end_time_utc)
            if start <= current_time <= end:
                active.append(window)
        return active

    def is_in_blackout_window(self, events: list[EconomicEvent], now: datetime | None = None) -> bool:
        return bool(self.get_active_blackouts(events, now))

