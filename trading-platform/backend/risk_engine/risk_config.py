from backend.risk_engine.risk_models import RiskConfig


DEFAULT_RISK_CONFIG = RiskConfig(
    max_risk_per_trade_percent=1.0,
    max_daily_drawdown_percent=3.0,
    max_consecutive_losses=3,
    max_allowed_spread=30.0,
    max_allowed_slippage=10.0,
    trading_enabled=True,
)


def get_default_risk_config() -> RiskConfig:
    """Return a copy of centralized default risk limits."""

    return DEFAULT_RISK_CONFIG.model_copy(deep=True)

