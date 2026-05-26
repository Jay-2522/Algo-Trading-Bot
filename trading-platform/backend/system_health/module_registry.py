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
    {"name": "institutional_breaker_blocks", "route": "/institutional/breakers/{symbol}"},
    {"name": "institutional_structure_shift", "route": "/institutional/structure-shift/{symbol}"},
    {"name": "institutional_confluence", "route": "/institutional/confluence/{symbol}"},
    {"name": "institutional_alignment", "route": "/institutional/alignment/{symbol}"},
    {"name": "institutional_session_intelligence", "route": "/institutional/session/{symbol}"},
    {"name": "institutional_entry_models", "route": "/institutional/entry-models/{symbol}"},
    {"name": "institutional_setup_validation", "route": "/institutional/setup-validation/{symbol}"},
    {"name": "institutional_simulation_decision", "route": "/institutional/simulation-decision/{symbol}"},
    {"name": "institutional_paper_trades", "route": "/institutional/paper-trades/{symbol}"},
    {"name": "institutional_position_management", "route": "/institutional/position-management/{symbol}"},
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
