import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

DOC_PATH = PROJECT_ROOT / "docs/phase20-day2-xauusd-end-to-end-validation.md"
MARKET_DATA_PATH = PROJECT_ROOT / "backend/mt5_demo/mt5_market_data_service.py"
BACKFILL_PATH = PROJECT_ROOT / "backend/mt5_demo/mt5_historical_backfill_service.py"
APPROVAL_PATH = PROJECT_ROOT / "backend/mt5_demo/demo_approval_workflow_service.py"
GUARDED_PATH = PROJECT_ROOT / "backend/mt5_demo/guarded_demo_order_sender_service.py"
SIGNAL_ENGINE_PATH = PROJECT_ROOT / "backend/strategy/client_signal_engine.py"
DASHBOARD_PATH = PROJECT_ROOT / "frontend/components/dashboard/DashboardShell.tsx"


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def _client() -> TestClient:
    from backend.main import app

    return TestClient(app)


def verify_doc_exists() -> bool:
    text = DOC_PATH.read_text(encoding="utf-8") if DOC_PATH.exists() else ""
    required = [
        "market-data",
        "strategy signal",
        "approval workflow",
        "RUNTIME_SYMBOL_NOT_ENABLED",
        "No live trading",
        "No fake XAUUSD bid/ask",
    ]
    missing = [item for item in required if item.lower() not in text.lower()]
    return show("XAUUSD validation documentation exists", DOC_PATH.exists() and not missing, ", ".join(missing))


def verify_market_data_routes_honest() -> bool:
    client = _client()
    status = client.get("/mt5-demo/market-data/status")
    tick = client.get("/mt5-demo/market-data/tick/XAUUSD")
    spread = client.get("/mt5-demo/market-data/spread/XAUUSD")
    acceptable_statuses = {
        "OK",
        "STALE_OR_MARKET_CLOSED",
        "SYMBOL_NOT_FOUND",
        "SYMBOL_HIDDEN",
        "SYMBOL_NOT_AVAILABLE",
        "SYMBOL_UNAVAILABLE",
        "SYMBOL_TICK_UNAVAILABLE",
        "MT5_UNAVAILABLE",
        "TICK_READ_FAILED",
    }
    tick_json = tick.json()
    spread_json = spread.json()
    tick_status = tick_json.get("status")
    if tick_status == "OK":
        honest_tick = (
            tick_json.get("freshness") == "READY"
            and isinstance(tick_json.get("bid"), (int, float))
            and isinstance(tick_json.get("ask"), (int, float))
            and tick_json["bid"] > 0
            and tick_json["ask"] > 0
            and tick_json["ask"] > tick_json["bid"]
        )
    else:
        honest_tick = tick_status in acceptable_statuses and tick_json.get("freshness") in {"OFFLINE", "STALE", None}
    passed = (
        status.status_code == 200
        and tick.status_code == 200
        and spread.status_code == 200
        and tick_json.get("symbol") == "XAUUSD"
        and spread_json.get("symbol") == "XAUUSD"
        and honest_tick
        and tick_json.get("live_execution_enabled") is False
        and tick_json.get("broker_execution_enabled") is False
    )
    return show("XAUUSD market-data routes classify real feed state honestly", passed, str(tick_json))


def verify_history_routes_work() -> bool:
    client = _client()
    m5 = client.get("/mt5-demo/history/XAUUSD/M5/summary")
    h1 = client.get("/mt5-demo/history/XAUUSD/H1/summary")
    acceptable = {"OK", "HISTORY_UNAVAILABLE", "CANDLES_UNAVAILABLE", "SYMBOL_NOT_FOUND", "SYMBOL_HIDDEN", "SYMBOL_UNAVAILABLE", "MT5_UNAVAILABLE", "CANDLE_READ_FAILED"}
    m5_json = m5.json()
    h1_json = h1.json()
    passed = (
        m5.status_code == 200
        and h1.status_code == 200
        and m5_json.get("symbol") == "XAUUSD"
        and h1_json.get("symbol") == "XAUUSD"
        and m5_json.get("timeframe") == "M5"
        and h1_json.get("timeframe") == "H1"
        and m5_json.get("status") in acceptable
        and h1_json.get("status") in acceptable
        and m5_json.get("live_execution_enabled") is False
        and h1_json.get("broker_execution_enabled") is False
    )
    return show("XAUUSD M5/H1 history summaries work or return explicit blocker", passed)


def verify_xauusd_signal_honesty() -> bool:
    client = _client()
    response = client.get("/client-signals-engine/XAUUSD")
    payload = response.json()
    valid_signal = payload.get("signal") in {"BUY", "SELL", "WAIT"}
    honest_wait = payload.get("signal") != "WAIT" or payload.get("confidence") is None
    no_execution = payload.get("live_execution_enabled") is False and payload.get("broker_execution_enabled") is False
    components = payload.get("strategy_components") or {}
    component_keys = {"liquidity_sweep", "bos", "choch", "fvg", "order_block", "session_valid"}
    passed = response.status_code == 200 and payload.get("symbol") == "XAUUSD" and valid_signal and honest_wait and no_execution and component_keys <= set(components)
    return show("XAUUSD signal route exposes only real strategy output", passed, str(payload))


def verify_xauusd_approval_workflow_safe() -> bool:
    client = _client()
    payload = {
        "environment": "DEMO",
        "symbol": "XAUUSD",
        "action": "BUY",
        "lot": 0.01,
        "entry_price": 2350.0,
        "stop_loss": 2345.0,
        "take_profit": 2360.0,
        "manual_confirmation": True,
        "acknowledge_no_live_trading": True,
        "acknowledge_demo_only": True,
        "acknowledge_no_order_placement_today": True,
        "live_execution_enabled": False,
        "broker_execution_enabled": False,
        "execution_allowed": False,
    }
    response = client.post("/mt5-demo/demo-approval-workflow/run", json=payload)
    result = response.json()
    passed = (
        response.status_code == 200
        and result.get("status") in {"APPROVED_FOR_FUTURE_SINGLE_DEMO_ORDER_TEST", "BLOCKED"}
        and result.get("mt5_order_sent") is False
        and result.get("would_send_to_mt5") is False
        and result.get("execution_allowed") is False
        and result.get("live_execution_enabled") is False
        and result.get("broker_execution_enabled") is False
    )
    return show("XAUUSD approval workflow validates safely without sending", passed, str(result.get("blockers", [])))


def verify_xauusd_runtime_send_still_blocked() -> bool:
    client = _client()
    payload = {
        "environment": "DEMO",
        "symbol": "XAUUSD",
        "action": "BUY",
        "lot": 0.01,
        "entry_price": 2350.0,
        "stop_loss": 2345.0,
        "take_profit": 2360.0,
        "manual_confirmation": True,
        "acknowledge_demo_only": True,
        "acknowledge_no_live_trading": True,
        "acknowledge_single_trade_only": True,
        "live_execution_enabled": False,
        "broker_execution_enabled": False,
        "execution_allowed": False,
    }
    response = client.post("/mt5-demo/guarded-demo-order/prepare", json=payload)
    result = response.json()
    blockers = result.get("blockers") or []
    passed = (
        response.status_code == 200
        and result.get("mt5_order_sent") is False
        and result.get("demo_order_attempted") is False
        and "RUNTIME_SYMBOL_NOT_ENABLED" in blockers
        and result.get("live_execution_enabled") is False
        and result.get("broker_execution_enabled") is False
    )
    return show("XAUUSD guarded runtime order remains future-only", passed, str(blockers))


def verify_source_support_and_dashboard_labels() -> bool:
    market_data = MARKET_DATA_PATH.read_text(encoding="utf-8")
    backfill = BACKFILL_PATH.read_text(encoding="utf-8")
    approval = APPROVAL_PATH.read_text(encoding="utf-8")
    guarded = GUARDED_PATH.read_text(encoding="utf-8")
    signal = SIGNAL_ENGINE_PATH.read_text(encoding="utf-8")
    dashboard = DASHBOARD_PATH.read_text(encoding="utf-8")
    required = [
        "supported_symbols = {\"EURUSD\", \"XAUUSD\"}",
        "mt5.symbol_select(symbol, True)",
        "allowed_symbols = {\"EURUSD\", \"XAUUSD\"}",
        "runtime_symbols = {\"EURUSD\"}",
        "RUNTIME_SYMBOL_NOT_ENABLED",
        "symbol_info = mt5.symbol_info(symbol)",
        "xauusdReadinessLabel",
        "Market Ready",
        "Market Closed / Feed Offline",
        "Symbol Not Available",
        "Waiting for Strategy Setup",
        "Ready for Future Demo Test",
    ]
    combined = "\n".join([market_data, backfill, approval, guarded, signal, dashboard])
    missing = [item for item in required if item not in combined]
    return show("Source supports XAUUSD validation and dashboard readiness labels", not missing, ", ".join(missing))


def verify_no_order_send_in_tests_or_new_paths() -> bool:
    token = "mt5." + "order_send"
    this_test_text = Path(__file__).read_text(encoding="utf-8", errors="ignore")
    test_matches = [Path(__file__).relative_to(PROJECT_ROOT).as_posix()] if token in this_test_text else []
    backend_matches = [
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in (PROJECT_ROOT / "backend").rglob("*.py")
        if token in path.read_text(encoding="utf-8", errors="ignore")
    ]
    allowed_backend = [
        "backend/demo_execution/mt5_demo_executor.py",
        "backend/mt5_demo/guarded_demo_order_sender_service.py",
    ]
    safety_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in [MARKET_DATA_PATH, BACKFILL_PATH, APPROVAL_PATH, SIGNAL_ENGINE_PATH]
    )
    forbidden = ['"live_execution_enabled": True', '"broker_execution_enabled": True', '"execution_allowed": True']
    present = [item for item in forbidden if item in safety_text]
    passed = not test_matches and sorted(backend_matches) == allowed_backend and not present
    return show("No test order_send, no new order path, no live/broker enablement", passed, ", ".join(test_matches + backend_matches + present))


def main() -> int:
    print("Phase 20 Day 2 XAUUSD End-to-End Validation")
    print("=" * 78)
    checks = [
        verify_doc_exists(),
        verify_market_data_routes_honest(),
        verify_history_routes_work(),
        verify_xauusd_signal_honesty(),
        verify_xauusd_approval_workflow_safe(),
        verify_xauusd_runtime_send_still_blocked(),
        verify_source_support_and_dashboard_labels(),
        verify_no_order_send_in_tests_or_new_paths(),
    ]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
