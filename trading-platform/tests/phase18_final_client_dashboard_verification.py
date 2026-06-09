import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

DASHBOARD_PATH = PROJECT_ROOT / "frontend/components/dashboard/DashboardShell.tsx"
HISTORY_PATH = PROJECT_ROOT / "frontend/components/dashboard/TradeHistoryPage.tsx"
HISTORY_ROUTE_PATH = PROJECT_ROOT / "frontend/app/dashboard/history/page.tsx"
API_PATH = PROJECT_ROOT / "frontend/lib/clientOperatingDashboardApi.ts"
DOC_PATH = PROJECT_ROOT / "docs/phase18-final-client-operating-dashboard.md"
GLOBALS_PATH = PROJECT_ROOT / "frontend/app/globals.css"


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def verify_files_exist() -> bool:
    required_paths = [DASHBOARD_PATH, HISTORY_PATH, HISTORY_ROUTE_PATH, API_PATH, DOC_PATH]
    missing = [str(path.relative_to(PROJECT_ROOT)) for path in required_paths if not path.exists()]
    return show("Client dashboard files exist", not missing, ", ".join(missing))


def verify_api_helpers_exist() -> bool:
    text = API_PATH.read_text(encoding="utf-8")
    required = [
        "fetchClientOperatingDashboard",
        "previewClientDemoTrade",
        "sendGuardedClientDemoTrade",
        "syncClientPositionsToJournal",
        "syncClientLifecycle",
        "/mt5-demo/market-data/tick/EURUSD",
        "/mt5-demo/demo-approval-workflow/run",
        "/mt5-demo/guarded-demo-order/send",
        "/mt5-demo/positions/sync-journal",
        "/mt5-demo/lifecycle/sync",
        "fetchClientTradeHistory",
        "/trade-journal/persistence/recent?limit=",
    ]
    missing = [item for item in required if item not in text]
    return show("Dashboard API helpers exist", not missing, ", ".join(missing))


def verify_trade_panel_uses_safe_flow() -> bool:
    dashboard = DASHBOARD_PATH.read_text(encoding="utf-8")
    api = API_PATH.read_text(encoding="utf-8")
    passed = (
        "previewClientDemoTrade(orderPayload())" in dashboard
        and "sendGuardedClientDemoTrade(orderPayload())" in dashboard
        and "approved_for_future_demo_order" in dashboard
        and "execute_single_demo_order_now" in api
        and "manual_confirmation: true" in api
        and "acknowledge_demo_only: true" in api
        and "acknowledge_no_live_trading: true" in api
        and "acknowledge_single_trade_only: true" in api
    )
    return show("Trade panel does not bypass approval or guarded sender", passed)


def verify_no_direct_order_send_route_from_frontend() -> bool:
    frontend_text = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in (PROJECT_ROOT / "frontend").rglob("*") if path.is_file() and path.suffix in {".ts", ".tsx"})
    forbidden = ["/mt5-demo/order-send", "mt5.order_send", "order_send("]
    present = [item for item in forbidden if item in frontend_text]
    return show("Frontend does not use direct order send routes", not present, ", ".join(present))


def verify_trade_button_blocks() -> bool:
    text = DASHBOARD_PATH.read_text(encoding="utf-8")
    required = [
        "const canPreview = selectedMarketOpen && !openTradeExists && formValid && !workingAction",
        "const canSend = canPreview && approvalReady",
        "disabled={!canPreview}",
        "disabled={!canSend}",
        "Stop Loss",
        "Take Profit",
        "selectedSignal",
        "Preview is blocked until a EURUSD AI signal is ready",
    ]
    missing = [item for item in required if item not in text]
    return show("Market closed and missing SL/TP block preview/send", not missing, ", ".join(missing))


def verify_clean_client_sections() -> bool:
    text = DASHBOARD_PATH.read_text(encoding="utf-8")
    required = [
        "Account Status",
        "Account Health",
        "Floating P&L",
        "Last Trade",
        "Market Overview",
        "AI Signal Center",
        "Signal Execution Panel",
        "Trade Status",
        "Open Trades",
        "Closed Demo Trades",
        "Performance Summary",
        "DEMO MODE",
        "LIVE TRADING DISABLED",
        "GUARDED EXECUTION ENABLED",
    ]
    missing = [item for item in required if item not in text]
    hidden = [
        "Readiness",
        "Approval workflow approved",
        "workflow_id",
        "audit_id",
        "preflight_id",
        "simulator_id",
        "execution_allowed raw",
        "broker_execution_enabled raw",
        "mt5_order_send_used raw",
        "sync_id",
        "verification_id",
    ]
    present = [item for item in hidden if item in text]
    return show("Client dashboard sections are clean and developer IDs hidden", not missing and not present, ", ".join(missing + present))


def verify_trade_history_page() -> bool:
    dashboard = DASHBOARD_PATH.read_text(encoding="utf-8")
    history = HISTORY_PATH.read_text(encoding="utf-8")
    route = HISTORY_ROUTE_PATH.read_text(encoding="utf-8")
    required = [
        "View Full Trade History",
        'href="/dashboard/history"',
        "fetchClientTradeHistory(500)",
        "Search by symbol",
        "Sort by date",
        "Completed trades will appear here.",
        "Previous",
        "Next",
        "formatTradeTime",
        "Date",
        "Symbol",
        "Direction",
        "Lot",
        "Entry",
        "Exit",
        "P&L",
        "Result",
        "Duration",
        "TradeHistoryPage",
    ]
    combined = "\n".join([dashboard, history, route])
    missing = [item for item in required if item not in combined]
    return show("Trade history page provides search, sort, pagination, and clean columns", not missing, ", ".join(missing))


def verify_human_timestamps_and_empty_states() -> bool:
    dashboard = DASHBOARD_PATH.read_text(encoding="utf-8")
    history = HISTORY_PATH.read_text(encoding="utf-8")
    required = [
        "formatTradeTime(readText(trade, [\"closed_at\", \"close_time\"], \"\"))",
        "whitespace-pre-line",
        "Waiting for the next AI-approved trade.",
        "Completed trades will appear here.",
        "Market feed unavailable.",
    ]
    forbidden = [
        "readText(trade, [\"closed_at\"], \"Unavailable\")",
        "No completed demo trades yet.",
    ]
    combined = "\n".join([dashboard, history])
    missing = [item for item in required if item not in combined]
    present = [item for item in forbidden if item in combined]
    return show("Timestamps and empty states are client-facing", not missing and not present, ", ".join(missing + present))


def verify_client_font_polish() -> bool:
    text = GLOBALS_PATH.read_text(encoding="utf-8")
    return show("Dashboard uses configured premium font stack", "var(--font-geist-sans), Inter" in text)


def verify_no_fake_data() -> bool:
    text = "\n".join([DASHBOARD_PATH.read_text(encoding="utf-8"), HISTORY_PATH.read_text(encoding="utf-8")])
    suspicious = [
        "fake",
        "mock",
        "placeholderPnl",
        "sampleTrade",
        "100000",
        "100003.13",
        "hardcoded",
    ]
    present = [item for item in suspicious if item.lower() in text.lower()]
    honest = "Unavailable" in text and "Need more closed trades." in text and "Completed trades will appear here." in text
    return show("No fake data appears in client dashboard", not present and honest, ", ".join(present))


def verify_auto_refresh_and_safe_sync() -> bool:
    text = DASHBOARD_PATH.read_text(encoding="utf-8")
    required = [
        "window.setInterval(() => void refresh(), 5000)",
        "Refresh Positions",
        "Sync Lifecycle",
        "syncClientPositionsToJournal",
        "syncClientLifecycle",
    ]
    missing = [item for item in required if item not in text]
    no_send_in_refresh = "sendGuardedClientDemoTrade" in text and "window.setInterval(() => void refresh(), 5000)" in text
    return show("Auto-refresh and manual sync are safe", not missing and no_send_in_refresh, ", ".join(missing))


def verify_backend_order_send_unchanged() -> bool:
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
    return show("No new backend mt5.order_send path exists", sorted(matches) == allowed, ", ".join(matches))


def verify_frontend_build_script_available() -> bool:
    package_text = (PROJECT_ROOT / "frontend/package.json").read_text(encoding="utf-8")
    return show("Frontend build script available", '"build": "next build"' in package_text)


def main() -> int:
    print("Phase 18 Final Client Dashboard Verification")
    print("=" * 78)
    checks = [
        verify_files_exist(),
        verify_api_helpers_exist(),
        verify_trade_panel_uses_safe_flow(),
        verify_no_direct_order_send_route_from_frontend(),
        verify_trade_button_blocks(),
        verify_clean_client_sections(),
        verify_trade_history_page(),
        verify_human_timestamps_and_empty_states(),
        verify_client_font_polish(),
        verify_no_fake_data(),
        verify_auto_refresh_and_safe_sync(),
        verify_backend_order_send_unchanged(),
        verify_frontend_build_script_available(),
    ]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
