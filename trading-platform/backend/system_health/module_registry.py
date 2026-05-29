MODULE_REGISTRY: list[dict] = [
    {"name": "core", "route": "/health"},
    {"name": "market_data", "route": "/market-data/timeframes"},
    {"name": "strategy", "route": "/strategy/session"},
    {"name": "risk", "route": "/risk/status"},
    {"name": "execution", "route": "/execution/status"},
    {"name": "execution_queue", "route": "/execution-queue/status"},
    {"name": "mt5", "route": "/mt5/status"},
    {"name": "monitoring", "route": "/monitoring/status"},
    {"name": "control_center", "route": "/control-center/status"},
    {"name": "mt5_demo_execution_bridge", "route": "/demo-execution/status"},
    {"name": "database", "route": "/database/status"},
    {"name": "ai", "route": "/ai/status"},
    {"name": "account_routing", "route": "/accounts/status"},
    {"name": "account_allocation", "route": "/accounts/allocation/status"},
    {"name": "vps_dashboard_backend", "route": "/dashboard/status"},
    {"name": "news", "route": "/news/status"},
    {"name": "orchestration", "route": "/orchestration/status"},
    {"name": "phase3_readiness", "route": "/phase3/status"},
    {"name": "backtesting", "route": "/backtesting/status"},
    {"name": "advanced_historical_replay", "route": "/replay/status"},
    {"name": "broker_compatibility", "route": "/brokers/status"},
    {"name": "broker_candle_feed", "route": "/brokers/candles/status"},
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
    {"name": "institutional_orchestration", "route": "/institutional/orchestration/{symbol}"},
    {"name": "institutional_reasoning", "route": "/institutional/reasoning/{symbol}"},
    {"name": "institutional_performance", "route": "/institutional/performance/{symbol}"},
    {"name": "institutional_dashboard", "route": "/institutional/dashboard/{symbol}"},
    {"name": "institutional_phase2_completion", "route": "/institutional/phase2/status"},
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
