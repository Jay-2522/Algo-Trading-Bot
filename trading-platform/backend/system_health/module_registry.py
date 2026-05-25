MODULE_REGISTRY: list[dict] = [
    {"name": "core", "route": "/health"},
    {"name": "market_data", "route": "/market-data/timeframes"},
    {"name": "strategy", "route": "/strategy/session"},
    {"name": "risk", "route": "/risk/status"},
    {"name": "execution", "route": "/execution/status"},
    {"name": "mt5", "route": "/mt5/status"},
    {"name": "database", "route": "/database/status"},
    {"name": "ai", "route": "/ai/status"},
    {"name": "news", "route": "/news/status"},
    {"name": "orchestration", "route": "/orchestration/status"},
    {"name": "backtesting", "route": "/backtesting/status"},
    {"name": "streaming", "route": "/streaming/status"},
    {"name": "trading_loop", "route": "/trading-loop/status"},
    {"name": "trade_journal", "route": "/trade-journal/status"},
    {"name": "system_health", "route": "/system/status"},
    {"name": "institutional_intelligence", "route": "/institutional/status"},
    {"name": "institutional_liquidity_sweeps", "route": "/institutional/sweeps/{symbol}"},
    {"name": "institutional_fvg", "route": "/institutional/fvg/{symbol}"},
    {"name": "institutional_order_blocks", "route": "/institutional/order-blocks/{symbol}"},
]


def get_module_registry() -> list[dict]:
    """Return immutable-by-caller module safety definitions."""

    return [
        {
            **module,
            "simulation_only": True,
            "live_execution_enabled": False,
        }
        for module in MODULE_REGISTRY
    ]
