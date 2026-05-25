from backend.trading_loop.loop_models import LoopConfig


def get_default_loop_config() -> LoopConfig:
    """Return controlled defaults with an enforced five-second minimum interval."""

    return LoopConfig(
        enabled=False,
        simulation_only=True,
        live_execution_enabled=False,
        interval_seconds=10,
        max_symbols_per_cycle=5,
        monitored_symbols=["XAUUSD"],
    )
