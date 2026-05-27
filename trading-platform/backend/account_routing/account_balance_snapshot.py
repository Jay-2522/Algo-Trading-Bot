from backend.account_routing.account_risk_profile import AccountRiskProfileEngine
from backend.account_routing.allocation_models import AccountBalanceSnapshot


class AccountBalanceSnapshotEngine:
    """Generate simulated JSON-safe account balance snapshots."""

    def __init__(self, risk_profile_engine: AccountRiskProfileEngine | None = None) -> None:
        self.risk_profile_engine = risk_profile_engine or AccountRiskProfileEngine()

    def get_balance_snapshot(self, account_id: str) -> AccountBalanceSnapshot | None:
        profile = self.risk_profile_engine.get_profile(account_id)
        if profile is None:
            return None
        return self._snapshot(profile)

    def get_all_snapshots(self) -> list[AccountBalanceSnapshot]:
        return [self._snapshot(profile) for profile in self.risk_profile_engine.get_profiles()]

    def _snapshot(self, profile) -> AccountBalanceSnapshot:
        warnings: list[str] = []
        healthy = True
        if not profile.enabled:
            warnings.append("Account is disabled.")
            healthy = False
        if profile.free_margin <= 0:
            warnings.append("Free margin unavailable in simulated snapshot.")
            healthy = False
        margin_level = (profile.equity / max(profile.balance - profile.free_margin + 1.0, 1.0)) * 100
        return AccountBalanceSnapshot(
            account_id=profile.account_id,
            broker_id=profile.broker_id,
            balance=profile.balance,
            equity=profile.equity,
            free_margin=profile.free_margin,
            margin_level=round(margin_level, 2),
            floating_pnl=round(profile.equity - profile.balance, 2),
            healthy=healthy,
            warnings=warnings,
        )
