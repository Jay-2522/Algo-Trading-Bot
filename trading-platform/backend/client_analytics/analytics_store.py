from backend.client_analytics.analytics_models import ClientAnalyticsOverview


class AnalyticsStore:
    """In-memory analytics snapshot store for client dashboard summaries."""

    _snapshots: list[ClientAnalyticsOverview] = []

    def store_snapshot(self, snapshot: ClientAnalyticsOverview) -> ClientAnalyticsOverview:
        self._snapshots.insert(0, snapshot)
        self._snapshots = self._snapshots[:1000]
        return snapshot

    def list_snapshots(self, limit: int = 100) -> list[ClientAnalyticsOverview]:
        bounded_limit = max(1, min(int(limit), 1000))
        return self._snapshots[:bounded_limit]

    def get_latest_snapshot(self) -> ClientAnalyticsOverview | None:
        return self._snapshots[0] if self._snapshots else None
