from backend.execution_risk.execution_risk_models import ExecutionRiskPolicy


class ExecutionRiskPolicyProvider:
    """Provide the default Phase 5 demo execution risk policy."""

    def get_policy(self) -> ExecutionRiskPolicy:
        return ExecutionRiskPolicy(
            allowed_symbols=["EURUSD"],
            blocked_symbols=["XAUUSD", "NIFTY50"],
            max_lot_per_account=0.01,
            max_target_accounts=3,
            max_daily_demo_attempts=20,
            require_demo_account=True,
            require_confirmation=True,
            live_execution_enabled=False,
            broker_execution_enabled=False,
            simulation_only=True,
            demo_execution=True,
        )
