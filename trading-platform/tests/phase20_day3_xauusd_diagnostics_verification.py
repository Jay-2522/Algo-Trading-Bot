import sys
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

MARKET_DATA_PATH = PROJECT_ROOT / "backend/mt5_demo/mt5_market_data_service.py"
ROUTES_PATH = PROJECT_ROOT / "backend/api/mt5_demo_routes.py"


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def verify_diagnostics_route_exists() -> bool:
    text = ROUTES_PATH.read_text(encoding="utf-8")
    required = [
        '@router.get("/diagnostics/xauusd")',
        "get_xauusd_diagnostics",
    ]
    missing = [item for item in required if item not in text]
    return show("XAUUSD diagnostics endpoint exists", not missing, ", ".join(missing))


def verify_diagnostics_response_shape() -> bool:
    from backend.main import app

    client = TestClient(app)
    response = client.get("/mt5-demo/diagnostics/xauusd")
    payload = response.json()
    required = {
        "symbol",
        "initialization_state",
        "classification",
        "diagnostic_report",
        "simulation_only",
        "live_execution_enabled",
        "broker_execution_enabled",
        "execution_allowed",
    }
    if payload.get("initialization_state") == "INITIALIZED":
        required |= {
            "account_login",
            "server",
            "terminal_path",
            "terminal_build",
            "terminal_symbol_count",
            "symbol_info",
            "symbol_info_tick",
            "symbol_visibility",
            "symbol_select_result",
            "mt5_last_error",
        }
    passed = (
        response.status_code == 200
        and payload.get("symbol") == "XAUUSD"
        and required <= set(payload)
        and payload.get("live_execution_enabled") is False
        and payload.get("broker_execution_enabled") is False
        and payload.get("execution_allowed") is False
    )
    print("Diagnostics classification:", payload.get("classification"))
    print("Diagnostics report:", payload.get("diagnostic_report"))
    return show("Diagnostics response is complete and read-only", passed)


def verify_visible_symbol_select_failure_not_unavailable() -> bool:
    from backend.mt5_demo.mt5_market_data_service import MT5MarketDataService

    service = MT5MarketDataService()
    info = SimpleNamespace(visible=True)
    result = service._classify_symbol("XAUUSD", info, False, (-3, "Terminal: Out of memory"))
    passed = (
        result["classification"] == "SYMBOL_AVAILABLE_SELECT_FAILED"
        and "symbol_select() failed" in result["message"]
        and result["symbol_select_result"] is False
    )
    return show("Visible symbol is not classified unavailable when symbol_select fails", passed, str(result))


def verify_hidden_and_missing_classifications() -> bool:
    from backend.mt5_demo.mt5_market_data_service import MT5MarketDataService

    service = MT5MarketDataService()
    hidden = service._classify_symbol("XAUUSD", SimpleNamespace(visible=False), False, (-1, "hidden"))
    missing = service._classify_symbol("XAUUSD", None, False, None)
    passed = hidden["classification"] == "SYMBOL_HIDDEN" and missing["classification"] == "SYMBOL_NOT_FOUND"
    return show("SYMBOL_HIDDEN and SYMBOL_NOT_FOUND are distinct", passed, f"{hidden}; {missing}")


def verify_market_data_logic_uses_symbol_info() -> bool:
    text = MARKET_DATA_PATH.read_text(encoding="utf-8")
    required = [
        "def get_xauusd_diagnostics",
        "def get_symbol_diagnostics",
        "symbol_info_tick",
        "symbol_select_result",
        "SYMBOL_AVAILABLE_SELECT_FAILED",
        "SYMBOL_TICK_UNAVAILABLE",
        "SYMBOL_NOT_FOUND",
        "SYMBOL_HIDDEN",
        "symbol_info() returned a visible symbol",
    ]
    forbidden = [
        'return self._error_payload(normalized, "SYMBOL_NOT_AVAILABLE", visibility_error)',
        'return self._candle_error_payload(normalized, normalized_timeframe, count, "SYMBOL_UNAVAILABLE", visibility_error)',
    ]
    missing = [item for item in required if item not in text]
    present = [item for item in forbidden if item in text]
    return show("Market-data validation uses symbol_info availability, not only symbol_select", not missing and not present, ", ".join(missing + present))


def verify_no_execution_changes() -> bool:
    order_token = "mt5." + "order_send"
    backend_matches = [
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in (PROJECT_ROOT / "backend").rglob("*.py")
        if order_token in path.read_text(encoding="utf-8", errors="ignore")
    ]
    allowed_backend = [
        "backend/demo_execution/mt5_demo_executor.py",
        "backend/mt5_demo/guarded_demo_order_sender_service.py",
    ]
    changed_text = MARKET_DATA_PATH.read_text(encoding="utf-8") + ROUTES_PATH.read_text(encoding="utf-8")
    forbidden = ['"live_execution_enabled": True', '"broker_execution_enabled": True', '"execution_allowed": True']
    present = [item for item in forbidden if item in changed_text]
    test_text = Path(__file__).read_text(encoding="utf-8")
    test_mentions_order_send = order_token in test_text
    passed = sorted(backend_matches) == allowed_backend and not present and not test_mentions_order_send
    return show("No execution path, live flag, or broker flag was added", passed, ", ".join(backend_matches + present))


def main() -> int:
    print("Phase 20 Day 3 XAUUSD Diagnostics Verification")
    print("=" * 78)
    checks = [
        verify_diagnostics_route_exists(),
        verify_diagnostics_response_shape(),
        verify_visible_symbol_select_failure_not_unavailable(),
        verify_hidden_and_missing_classifications(),
        verify_market_data_logic_uses_symbol_info(),
        verify_no_execution_changes(),
    ]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
