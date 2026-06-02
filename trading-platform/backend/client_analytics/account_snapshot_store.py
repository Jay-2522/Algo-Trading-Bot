from backend.client_analytics.account_models import AccountAnalyticsSummary


class AccountSnapshotStore:
    """In-memory account analytics snapshot store."""

    _snapshots: list[AccountAnalyticsSummary] = []

    def store_snapshot(self, snapshot: AccountAnalyticsSummary) -> AccountAnalyticsSummary:
        self._snapshots.insert(0, snapshot)
        self._snapshots = self._snapshots[:1000]
        return snapshot

    def list_snapshots(self, limit: int = 100) -> list[AccountAnalyticsSummary]:
        bounded_limit = max(1, min(int(limit), 1000))
        return self._snapshots[:bounded_limit]

    def get_latest_for_account(self, account_id: str) -> AccountAnalyticsSummary | None:
        account_key = str(account_id or "").upper()
        return next((snapshot for snapshot in self._snapshots if snapshot.account_id.upper() == account_key), None)
