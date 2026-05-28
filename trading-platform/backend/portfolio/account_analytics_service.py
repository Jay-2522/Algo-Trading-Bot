from backend.account_routing.account_registry import AccountRegistry
from backend.account_routing.account_risk_profile import AccountRiskProfileEngine
from backend.account_routing.account_balance_snapshot import AccountBalanceSnapshotEngine
from backend.portfolio.portfolio_models import PortfolioAccountSummary


class AccountAnalyticsService:
    """Build dashboard-ready simulated account analytics."""

    def __init__(
        self,
        account_registry: AccountRegistry | None = None,
        risk_profile_engine: AccountRiskProfileEngine | None = None,
        balance_snapshot_engine: AccountBalanceSnapshotEngine | None = None,
    ) -> None:
        self.account_registry = account_registry or AccountRegistry()
        self.risk_profile_engine = risk_profile_engine or AccountRiskProfileEngine(self.account_registry)
        self.balance_snapshot_engine = balance_snapshot_engine or AccountBalanceSnapshotEngine(self.risk_profile_engine)

    def get_accounts(self) -> list[PortfolioAccountSummary]:
        accounts = {account.account_id: account for account in self.account_registry.list_accounts()}
        snapshots = {snapshot.account_id: snapshot for snapshot in self.balance_snapshot_engine.get_all_snapshots()}
        summaries: list[PortfolioAccountSummary] = []
        for profile in self.risk_profile_engine.get_profiles():
            account = accounts.get(profile.account_id)
            snapshot = snapshots.get(profile.account_id)
            issues = self.risk_profile_engine.validate_profile(profile)[1]
            risk_status = "READY" if not issues else "DISABLED" if not profile.enabled else "WARNING"
            summaries.append(
                PortfolioAccountSummary(
                    account_id=profile.account_id,
                    broker_id=profile.broker_id,
                    account_mode=profile.account_mode,
                    balance=snapshot.balance if snapshot else profile.balance,
                    equity=snapshot.equity if snapshot else profile.equity,
                    free_margin=snapshot.free_margin if snapshot else profile.free_margin,
                    enabled=profile.enabled,
                    demo_ready=profile.demo_ready,
                    supported_symbols=account.supported_symbols if account else [],
                    risk_status=risk_status,
                    simulation_only=True,
                    live_execution_enabled=False,
                )
            )
        return summaries
