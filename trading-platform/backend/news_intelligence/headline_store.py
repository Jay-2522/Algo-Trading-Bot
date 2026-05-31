from datetime import datetime, timedelta, timezone

from backend.news_intelligence.headline_models import HeadlineEvent


class HeadlineStore:
    """In-memory headline store for manual/test payloads only."""

    _headlines: dict[str, HeadlineEvent] = {}

    def upsert_headlines(self, headlines: list[HeadlineEvent]) -> list[HeadlineEvent]:
        for headline in headlines:
            self._headlines[headline.headline_id] = headline
        return self.list_headlines()

    def list_headlines(self, limit: int = 100) -> list[HeadlineEvent]:
        return sorted(self._headlines.values(), key=lambda headline: headline.timestamp, reverse=True)[:limit]

    def recent_headlines(self, minutes: int = 60) -> list[HeadlineEvent]:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        return [headline for headline in self.list_headlines() if headline.timestamp >= cutoff]

    def active_headlines(self) -> list[HeadlineEvent]:
        return [headline for headline in self.list_headlines() if headline.active]

    def clear(self) -> None:
        self._headlines.clear()
