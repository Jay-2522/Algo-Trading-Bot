from datetime import datetime
from typing import Any

from backend.account_routing.account_routing_service import AccountRoutingService
from backend.client_analytics.account_models import AccountAnalyticsSummary
from backend.client_analytics.account_snapshot_store import AccountSnapshotStore
from backend.client_analytics.analytics_data_collector import AnalyticsDataCollector


class AccountAnalyticsService:
    """Account-level analytics for master and demo copier accounts."""

    MASTER_ACCOUNT_ID = "MASTER_DEMO"

    def __init__(
        self,
        routing_service: AccountRoutingService | None = None,
        collector: AnalyticsDataCollector | None = None,
        store: AccountSnapshotStore | None = None,
    ) -> None:
        self.routing_service = routing_service or AccountRoutingService()
        self.collector = collector or AnalyticsDataCollector()
        self.store = store or AccountSnapshotStore()

    def get_accounts(self) -> list[AccountAnalyticsSummary]:
        accounts = [self.get_master_account(), *self.get_copier_accounts()]
        for account in accounts:
            self.store.store_snapshot(account)
        return accounts

    def get_account(self, account_id: str) -> AccountAnalyticsSummary | None:
        account_key = str(account_id or "").upper()
        return next((account for account in self.get_accounts() if account.account_id.upper() == account_key), None)

    def get_master_account(self) -> AccountAnalyticsSummary:
        data = self.collector.collect_all()
        executions = data.get("demo_executions", [])
        return AccountAnalyticsSummary(
            account_id=self.MASTER_ACCOUNT_ID,
            account_name="Master Demo Account",
            account_type="MASTER",
            total_signals=len(data.get("strategy_signals", [])),
            total_executions=len(executions),
            total_copied_trades=0,
            win_rate=0.0,
            net_pnl=0.0,
            max_drawdown=0.0,
            synchronization_status=self._overall_sync_status(),
            last_sync_time=self._last_sync_time(),
            simulation_only=True,
            demo_execution=True,
            live_execution_enabled=False,
            broker_execution_enabled=False,
        )

    def get_copier_accounts(self) -> list[AccountAnalyticsSummary]:
        registry_accounts = [
            account
            for account in self.routing_service.list_accounts()
            if account.account_id in {"STARTRADER_DEMO_1", "FXPRO_DEMO_1", "VANTAGE_DEMO_1"}
        ]
        return [self._summary_for_copier(account) for account in registry_accounts]

    def get_sync_status(self) -> dict[str, Any]:
        accounts = self.get_accounts()
        statuses = [account.synchronization_status for account in accounts if account.account_type == "COPIER"]
        if not statuses:
            status = "UNKNOWN"
        elif all(item == "SYNCHRONIZED" for item in statuses):
            status = "SYNCHRONIZED"
        elif any(item == "DEGRADED" for item in statuses):
            status = "DEGRADED"
        else:
            status = "PENDING"
        return {
            "synchronization_status": status,
            "copier_health": status,
            "supported_symbols": ["XAUUSD", "EURUSD", "NIFTY50"],
            "nifty50_status": "ANALYTICS_INTEGRATED",
            "last_sync_time": self._last_sync_time(),
            "execution_consistency": "NO_COPIER_ACTIVITY" if status in {"PENDING", "UNKNOWN"} else status,
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def get_account_performance(self) -> dict[str, Any]:
        accounts = self.get_accounts()
        return {
            "accounts": accounts,
            "supported_symbols": ["XAUUSD", "EURUSD", "NIFTY50"],
            "nifty50_status": "ANALYTICS_INTEGRATED",
            "total_accounts": len(accounts),
            "active_copiers": len([account for account in accounts if account.account_type == "COPIER"]),
            "total_executions": sum(account.total_executions for account in accounts),
            "total_copied_trades": sum(account.total_copied_trades for account in accounts),
            "net_pnl": 0.0,
            "win_rate": 0.0,
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def _summary_for_copier(self, account) -> AccountAnalyticsSummary:
        copied_count = self._copied_count(account.account_id)
        failed_count = self._failed_count(account.account_id)
        status = self._account_sync_status(account.account_id, copied_count, failed_count)
        return AccountAnalyticsSummary(
            account_id=account.account_id,
            account_name=account.display_name,
            account_type="COPIER",
            total_signals=0,
            total_executions=copied_count + failed_count,
            total_copied_trades=copied_count,
            win_rate=0.0,
            net_pnl=0.0,
            max_drawdown=0.0,
            synchronization_status=status,
            last_sync_time=self._last_sync_time(account.account_id),
            simulation_only=True,
            demo_execution=True,
            live_execution_enabled=False,
            broker_execution_enabled=False,
        )

    def _copier_results(self) -> list[Any]:
        return self.collector.collect_trade_copier_results()

    def _copy_batches(self) -> list[Any]:
        try:
            from backend.api.trade_copier_routes import trade_copier_service

            return trade_copier_service.list_batches(1000)
        except Exception:
            return []

    def _copied_count(self, account_id: str) -> int:
        results = self._copier_results()
        batches = self._copy_batches()
        from_results = sum(1 for result in results if account_id in getattr(result, "copied_accounts", []))
        from_batches = sum(
            1
            for batch in batches
            for item in getattr(batch, "account_copy_results", [])
            if getattr(item, "account_id", "") == account_id and bool(getattr(item, "copied", False))
        )
        return from_results + from_batches

    def _failed_count(self, account_id: str) -> int:
        results = self._copier_results()
        batches = self._copy_batches()
        from_results = sum(
            1
            for result in results
            if account_id in getattr(result, "failed_accounts", []) or account_id in getattr(result, "skipped_accounts", [])
        )
        from_batches = sum(
            1
            for batch in batches
            for item in getattr(batch, "account_copy_results", [])
            if getattr(item, "account_id", "") == account_id and getattr(item, "status", "") in {"REJECTED", "BLOCKED", "MT5_UNAVAILABLE", "FAILED_SAFE", "SKIPPED_DUPLICATE"}
        )
        return from_results + from_batches

    def _account_sync_status(self, account_id: str, copied_count: int, failed_count: int) -> str:
        if copied_count == 0 and failed_count == 0:
            return "PENDING"
        if failed_count > 0:
            return "DEGRADED"
        return "SYNCHRONIZED"

    def _overall_sync_status(self) -> str:
        copier_statuses = [account.synchronization_status for account in self.get_copier_accounts()]
        if not copier_statuses:
            return "UNKNOWN"
        if all(status == "SYNCHRONIZED" for status in copier_statuses):
            return "SYNCHRONIZED"
        if any(status == "DEGRADED" for status in copier_statuses):
            return "DEGRADED"
        return "PENDING"

    def _last_sync_time(self, account_id: str | None = None) -> datetime | None:
        timestamps: list[datetime] = []
        for result in self._copier_results():
            if account_id and account_id not in getattr(result, "copied_accounts", []) and account_id not in getattr(result, "failed_accounts", []) and account_id not in getattr(result, "skipped_accounts", []):
                continue
            timestamp = getattr(result, "timestamp", None)
            if timestamp:
                timestamps.append(timestamp)
        for batch in self._copy_batches():
            for item in getattr(batch, "account_copy_results", []):
                if account_id and getattr(item, "account_id", "") != account_id:
                    continue
                timestamp = getattr(item, "timestamp", None)
                if timestamp:
                    timestamps.append(timestamp)
        return max(timestamps) if timestamps else None
