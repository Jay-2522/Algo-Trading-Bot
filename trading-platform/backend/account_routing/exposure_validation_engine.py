from backend.account_routing.allocation_models import AccountRiskProfile


class ExposureValidationEngine:
    """Validate account and symbol exposure for allocation preview."""

    def validate_exposure(
        self,
        account: AccountRiskProfile,
        symbol: str,
        risk_percent: float,
    ) -> tuple[bool, list[str]]:
        issues: list[str] = []
        if account.live_execution_enabled:
            issues.append("Live execution is not allowed.")
        if not account.enabled:
            issues.append("Account is disabled.")
        if not account.demo_ready:
            issues.append("Account is not demo-ready.")
        if not account.read_only:
            issues.append("Account is not read-only verified.")
        if risk_percent > account.max_risk_percent:
            issues.append("Risk percent exceeds account max risk.")
        if risk_percent > account.max_symbol_exposure:
            issues.append("Risk percent exceeds max symbol exposure.")
        if account.daily_loss_limit <= 0:
            issues.append("Daily risk limit is unavailable for this account.")
        return not issues, issues
