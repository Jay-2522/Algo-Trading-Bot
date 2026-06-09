import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

DASHBOARD_PATH = PROJECT_ROOT / "frontend/components/dashboard/DashboardShell.tsx"
HISTORY_PATH = PROJECT_ROOT / "frontend/components/dashboard/TradeHistoryPage.tsx"
API_PATH = PROJECT_ROOT / "frontend/lib/clientOperatingDashboardApi.ts"
MAIN_PATH = PROJECT_ROOT / "backend/main.py"
MARKET_DATA_PATH = PROJECT_ROOT / "backend/mt5_demo/mt5_market_data_service.py"
SIGNAL_SERVICE_PATH = PROJECT_ROOT / "backend/strategy/client_signal_center_service.py"
SIGNAL_ROUTES_PATH = PROJECT_ROOT / "backend/api/client_signal_routes.py"
MARKET_SCOPE_ROUTES_PATH = PROJECT_ROOT / "backend/api/market_scope_routes.py"
DOC_PATH = PROJECT_ROOT / "docs/client-scoped-ai-trading-dashboard.md"


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def verify_files_and_routes() -> bool:
    required_paths = [SIGNAL_SERVICE_PATH, SIGNAL_ROUTES_PATH, MARKET_SCOPE_ROUTES_PATH, DOC_PATH]
    missing_paths = [str(path.relative_to(PROJECT_ROOT)) for path in required_paths if not path.exists()]
    main = MAIN_PATH.read_text(encoding="utf-8")
    routes = SIGNAL_ROUTES_PATH.read_text(encoding="utf-8") + MARKET_SCOPE_ROUTES_PATH.read_text(encoding="utf-8")
    required = [
        "client_signal_router",
        "market_scope_router",
        '@router.get("/status")',
        '@router.get("/current")',
        '@router.get("/{symbol}")',
        '@router.post("/refresh")',
        '@router.get("/instruments/status")',
    ]
    missing = [item for item in required if item not in main + routes]
    return show("Client signal and market scope routes exist", not missing_paths and not missing, ", ".join(missing_paths + missing))


def verify_dashboard_scope() -> bool:
    text = DASHBOARD_PATH.read_text(encoding="utf-8")
    required = [
        "AI Trading Dashboard",
        "EURUSD, XAUUSD, and NIFTY50 signal monitoring with guarded execution.",
        "Market Overview",
        "AI Signal Center",
        "Signal Execution Panel",
        "EURUSD",
        "XAUUSD",
        "NIFTY50",
    ]
    forbidden = ["GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "Quick Trade Panel", "Guarded Demo Order"]
    missing = [item for item in required if item not in text]
    present = [item for item in forbidden if item in text]
    return show("Dashboard is scoped to EURUSD/XAUUSD/NIFTY50", not missing and not present, ", ".join(missing + present))


def verify_xauusd_market_data_fix() -> bool:
    text = MARKET_DATA_PATH.read_text(encoding="utf-8")
    required = [
        "mt5.symbol_select(symbol, True)",
        "mt5.symbol_info_tick(normalized)",
        "info = mt5.symbol_info(normalized)",
        "SYMBOL_NOT_AVAILABLE",
        "STALE_OR_MARKET_CLOSED",
    ]
    missing = [item for item in required if item not in text]
    return show("XAUUSD market data selects symbol and classifies honestly", not missing, ", ".join(missing))


def verify_nifty_pending() -> bool:
    text = SIGNAL_SERVICE_PATH.read_text(encoding="utf-8") + MARKET_SCOPE_ROUTES_PATH.read_text(encoding="utf-8") + DASHBOARD_PATH.read_text(encoding="utf-8")
    required = [
        "PENDING_INDIAN_MARKET_INTEGRATION",
        "INTEGRATION_PENDING",
        "Indian market data/broker integration pending.",
        "Indian market integration pending.",
    ]
    missing = [item for item in required if item not in text]
    return show("NIFTY50 is integration pending without fake price", not missing, ", ".join(missing))


def verify_signal_center_honesty() -> bool:
    text = SIGNAL_SERVICE_PATH.read_text(encoding="utf-8")
    required = [
        '"signal": "WAIT"',
        '"confidence": None',
        "No confirmed setup available.",
        "strategy_consumed_feed",
        "risk_status = \"NO_SIGNAL\" if strategy.get(\"feed_ready\") else \"INSUFFICIENT_DATA\"",
    ]
    forbidden = ["fake BUY", "fake SELL", "confidence = 95", "confidence = 100"]
    missing = [item for item in required if item not in text]
    present = [item for item in forbidden if item in text]
    return show("Signal center returns WAIT/INSUFFICIENT_DATA honestly", not missing and not present, ", ".join(missing + present))


def verify_signal_based_execution_panel() -> bool:
    text = DASHBOARD_PATH.read_text(encoding="utf-8")
    required = [
        "selectedSignal",
        "selectedSymbol",
        "AI Direction",
        "Preview Signal Trade",
        "Confirm & Send Demo Order",
        "signalAction",
        "signalExecutable",
        "selectedSymbol === \"EURUSD\"",
    ]
    forbidden = ["<select", "setForm", "Manual", "Place Demo Trade"]
    missing = [item for item in required if item not in text]
    present = [item for item in forbidden if item in text]
    return show("Execution panel uses selected signal instead of manual direction", not missing and not present, ", ".join(missing + present))


def verify_history_scoped_filter() -> bool:
    text = HISTORY_PATH.read_text(encoding="utf-8")
    required = [
        "symbolFilter",
        "EURUSD",
        "XAUUSD",
        "NIFTY50",
        "All scoped symbols",
    ]
    missing = [item for item in required if item not in text]
    return show("Trade history filters scoped symbols", not missing, ", ".join(missing))


def verify_safe_order_paths() -> bool:
    api = API_PATH.read_text(encoding="utf-8")
    dashboard = DASHBOARD_PATH.read_text(encoding="utf-8")
    token = "mt5." + "order_send"
    matches = [
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in (PROJECT_ROOT / "backend").rglob("*.py")
        if token in path.read_text(encoding="utf-8", errors="ignore")
    ]
    allowed = [
        "backend/demo_execution/mt5_demo_executor.py",
        "backend/mt5_demo/guarded_demo_order_sender_service.py",
    ]
    passed = (
        sorted(matches) == allowed
        and "/mt5-demo/demo-approval-workflow/run" in api
        and "/mt5-demo/guarded-demo-order/send" in api
        and "previewClientDemoTrade(orderPayload())" in dashboard
        and "sendGuardedClientDemoTrade(orderPayload())" in dashboard
        and "live_execution_enabled: false" in api
        and "broker_execution_enabled: false" in api
    )
    return show("Guarded sender remains the only dashboard order path", passed, ", ".join(matches))


def verify_no_fake_data_or_confidence() -> bool:
    text = "\n".join(
        [
            DASHBOARD_PATH.read_text(encoding="utf-8"),
            HISTORY_PATH.read_text(encoding="utf-8"),
            SIGNAL_SERVICE_PATH.read_text(encoding="utf-8"),
        ]
    )
    forbidden = ["100003.13", "hardcoded", "sampleTrade", "placeholderPnl", "fake confidence", "fake signal"]
    present = [item for item in forbidden if item.lower() in text.lower()]
    return show("No fake trades, P&L, signals, or confidence", not present, ", ".join(present))


def verify_balance_nowrap_and_build_script() -> bool:
    dashboard = DASHBOARD_PATH.read_text(encoding="utf-8")
    package_text = (PROJECT_ROOT / "frontend/package.json").read_text(encoding="utf-8")
    passed = "whitespace-nowrap text-white" in dashboard and '"build": "next build"' in package_text
    return show("Balance/equity nowrap styles and frontend build script exist", passed)


def main() -> int:
    print("Client-Scoped AI Dashboard Verification")
    print("=" * 78)
    checks = [
        verify_files_and_routes(),
        verify_dashboard_scope(),
        verify_xauusd_market_data_fix(),
        verify_nifty_pending(),
        verify_signal_center_honesty(),
        verify_signal_based_execution_panel(),
        verify_history_scoped_filter(),
        verify_safe_order_paths(),
        verify_no_fake_data_or_confidence(),
        verify_balance_nowrap_and_build_script(),
    ]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
