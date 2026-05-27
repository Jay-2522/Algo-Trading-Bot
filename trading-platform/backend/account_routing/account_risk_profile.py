from backend.account_routing.account_models import BrokerAccountProfile
from backend.account_routing.account_registry import AccountRegistry
from backend.account_routing.allocation_models import AccountRiskProfile


class AccountRiskProfileEngine:
    """Maintain simulated account-level risk profiles for allocation previews."""

    def __init__(self, registry: AccountRegistry | None = None) -> None:
        self.registry = registry or AccountRegistry()

    def get_profiles(self) -> list[AccountRiskProfile]:
        return [self._profile_from_account(account) for account in self.registry.list_accounts()]

    def get_profile(self, account_id: str) -> AccountRiskProfile | None:
        account = self.registry.get_account(account_id)
        if account is None:
            return None
        return self._profile_from_account(account)

    def validate_profile(self, profile: AccountRiskProfile) -> tuple[bool, list[str]]:
        issues: list[str] = []
        if profile.live_execution_enabled:
            issues.append("Live execution must remain disabled.")
        if not profile.enabled:
            issues.append("Account profile is disabled.")
        if not profile.demo_ready:
            issues.append("Account profile is not demo-ready.")
        if not profile.read_only:
            issues.append("Account profile is not read-only.")
        if profile.balance <= 0 or profile.equity <= 0:
            issues.append("Account balance/equity must be positive.")
        return not issues, issues

    def _profile_from_account(self, account: BrokerAccountProfile) -> AccountRiskProfile:
        is_indian_placeholder = account.account_group == "INDIAN_BROKER_GROUP"
        return AccountRiskProfile(
            account_id=account.account_id,
            broker_id=account.broker_id,
            account_mode=account.account_mode,
            balance=10000.0,
            equity=10000.0,
            free_margin=10000.0,
            max_risk_percent=0.0 if is_indian_placeholder else 1.0,
            daily_loss_limit=0.0 if is_indian_placeholder else 5.0,
            max_lot_per_trade=0.0 if is_indian_placeholder else 1.0,
            max_symbol_exposure=0.0 if is_indian_placeholder else 3.0,
            enabled=account.enabled,
            demo_ready=account.demo_ready,
            read_only=account.read_only,
            simulation_only=True,
            live_execution_enabled=False,
        )
