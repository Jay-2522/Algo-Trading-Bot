import sys
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

MARKET_DATA_PATH = PROJECT_ROOT / "backend/mt5_demo/mt5_market_data_service.py"
DOC_PATH = PROJECT_ROOT / "docs/phase20-day4-xauusd-tick-recovery.md"


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def verify_doc_exists() -> bool:
    text = DOC_PATH.read_text(encoding="utf-8") if DOC_PATH.exists() else ""
    required = [
        "symbol_info_tick",
        "symbol_info",
        "TICK_AVAILABLE_DIRECT",
        "TICK_AVAILABLE_FROM_SYMBOL_INFO",
        "TICK_STILL_UNAVAILABLE",
        "terminal_memory_warning",
        "No price is generated or estimated",
    ]
    missing = [item for item in required if item.lower() not in text.lower()]
    return show("Day 4 tick recovery documentation exists", DOC_PATH.exists() and not missing, ", ".join(missing))


def verify_direct_tick_success_case() -> bool:
    from backend.mt5_demo.mt5_market_data_service import MT5MarketDataService

    service = MT5MarketDataService()
    tick = SimpleNamespace(bid=2350.12, ask=2350.45, time=1_700_000_000)
    info = SimpleNamespace(bid=0.0, ask=0.0, visible=True)
    recovery = service._recover_tick_quote("XAUUSD", tick, info, {"last_error": None})
    passed = (
        recovery["tick_recovery_status"] == "TICK_AVAILABLE_DIRECT"
        and recovery["source"] == "MT5_SYMBOL_INFO_TICK"
        and recovery["bid"] == 2350.12
        and recovery["ask"] == 2350.45
        and recovery["spread"] == 0.33
    )
    return show("Direct symbol_info_tick quote recovery works", passed, str(recovery))


def verify_symbol_info_fallback_success_case() -> bool:
    from backend.mt5_demo.mt5_market_data_service import MT5MarketDataService

    service = MT5MarketDataService()
    tick = None
    info = SimpleNamespace(bid=2349.7, ask=2350.1, last=2349.9, visible=True)
    availability = {
        "classification": "SYMBOL_AVAILABLE_SELECT_FAILED",
        "last_error": (-3, "Terminal: Out of memory"),
    }
    recovery = service._recover_tick_quote("XAUUSD", tick, info, availability)
    passed = (
        recovery["tick_recovery_status"] == "TICK_AVAILABLE_FROM_SYMBOL_INFO"
        and recovery["source"] == "MT5_SYMBOL_INFO_FIELDS"
        and recovery["bid"] == 2349.7
        and recovery["ask"] == 2350.1
        and recovery["spread"] == 0.4
    )
    return show("symbol_info bid/ask fallback works after symbol_select failure", passed, str(recovery))


def verify_unavailable_tick_remains_blocked() -> bool:
    from backend.mt5_demo.mt5_market_data_service import MT5MarketDataService

    service = MT5MarketDataService()
    tick = SimpleNamespace(bid=0.0, ask=0.0, time=0)
    info = SimpleNamespace(bid=0.0, ask=0.0, last=0.0, visible=True)
    availability = {
        "classification": "SYMBOL_AVAILABLE_SELECT_FAILED",
        "symbol_select_result": False,
        "last_error": (-3, "Terminal: Out of memory"),
        "message": "XAUUSD is visible, but symbol_select failed.",
    }
    recovery = service._recover_tick_quote("XAUUSD", tick, info, availability)
    blocked = service._stale_tick_payload("XAUUSD", recovery, availability)
    passed = (
        recovery["tick_recovery_status"] == "TICK_STILL_UNAVAILABLE"
        and blocked["status"] == "SYMBOL_TICK_UNAVAILABLE"
        and blocked["terminal_memory_warning"] is True
        and blocked["bid"] == 0.0
        and blocked["ask"] == 0.0
    )
    return show("Unavailable XAUUSD quote remains honestly blocked", passed, str(blocked))


def verify_tick_failure_debounce_uses_last_good_quote() -> bool:
    from backend.mt5_demo.mt5_market_data_service import MT5MarketDataService

    service = MT5MarketDataService()
    service._record_successful_tick(
        "XAUUSD",
        {
            "symbol": "XAUUSD",
            "bid": 2350.12,
            "ask": 2350.45,
            "spread": 0.33,
            "timestamp": service._timestamp(),
            "freshness": "READY",
            "source": "VANTAGE_DEMO",
            "status": "OK",
            "market_status": "MARKET_READY",
        },
    )
    first = service._temporary_tick_failure_payload("XAUUSD", "SYMBOL_TICK_UNAVAILABLE", "temporary miss")
    second = service._temporary_tick_failure_payload("XAUUSD", "SYMBOL_TICK_UNAVAILABLE", "temporary miss")
    third = service._temporary_tick_failure_payload("XAUUSD", "SYMBOL_TICK_UNAVAILABLE", "temporary miss")
    passed = (
        first["status"] == "STALE_TICK"
        and first["market_status"] == "STALE_TICK"
        and first["bid"] == 2350.12
        and first["ask"] == 2350.45
        and second["status"] == "STALE_TICK"
        and third["status"] == "FEED_OFFLINE"
        and third["bid"] == 2350.12
        and third["ask"] == 2350.45
    )
    return show("Temporary tick failures debounce to STALE_TICK before FEED_OFFLINE", passed, str({"first": first, "third": third}))


def verify_source_contains_recovery_logic() -> bool:
    text = MARKET_DATA_PATH.read_text(encoding="utf-8")
    required = [
        "_recover_tick_quote",
        "TICK_AVAILABLE_DIRECT",
        "TICK_AVAILABLE_FROM_SYMBOL_INFO",
        "TICK_STILL_UNAVAILABLE",
        "terminal_memory_warning",
        "MT5_SYMBOL_INFO_TICK",
        "MT5_SYMBOL_INFO_FIELDS",
        "symbol_info_bid",
        "symbol_info_ask",
        "calculated_spread",
        "recovery_status",
        "_temporary_tick_failure_payload",
        "STALE_TICK",
        "FEED_OFFLINE",
        "MARKET_READY",
    ]
    missing = [item for item in required if item not in text]
    return show("Market-data service includes tick recovery classifications", not missing, ", ".join(missing))


def verify_live_route_shape() -> bool:
    from backend.main import app

    client = TestClient(app)
    tick = client.get("/mt5-demo/market-data/tick/XAUUSD").json()
    diagnostics = client.get("/mt5-demo/diagnostics/xauusd").json()
    required_tick = {
        "symbol",
        "bid",
        "ask",
        "spread",
        "source",
        "tick_recovery_status",
        "symbol_availability",
        "mt5_last_error",
        "terminal_memory_warning",
    }
    required_diagnostics = {
        "direct_tick_result",
        "symbol_info_bid",
        "symbol_info_ask",
        "symbol_info_last",
        "calculated_spread",
        "recovery_status",
    }
    if tick.get("status") == "OK":
        honest = tick.get("bid", 0) > 0 and tick.get("ask", 0) > tick.get("bid", 0) and tick.get("spread", 0) > 0
        valid_recovery = tick.get("tick_recovery_status") in {"TICK_AVAILABLE_DIRECT", "TICK_AVAILABLE_FROM_SYMBOL_INFO"}
    else:
        honest = tick.get("tick_recovery_status") == "TICK_STILL_UNAVAILABLE" or tick.get("status") in {"STALE_TICK", "FEED_OFFLINE"}
        valid_recovery = tick.get("status") in {"SYMBOL_TICK_UNAVAILABLE", "STALE_TICK", "FEED_OFFLINE"}
    passed = (
        required_tick <= set(tick)
        and required_diagnostics <= set(diagnostics)
        and tick.get("symbol") == "XAUUSD"
        and honest
        and valid_recovery
        and tick.get("live_execution_enabled") is False
        and tick.get("broker_execution_enabled") is False
    )
    print("Live tick result:", tick)
    print("Diagnostics recovery:", diagnostics.get("recovery_status"))
    return show("Live XAUUSD route exposes recovery status honestly", passed)


def verify_no_fake_price_or_execution() -> bool:
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
    text = MARKET_DATA_PATH.read_text(encoding="utf-8")
    forbidden = [
        "base_price",
        "fake",
        '"live_execution_enabled": True',
        '"broker_execution_enabled": True',
        '"execution_allowed": True',
    ]
    present = [item for item in forbidden if item in text]
    test_text = Path(__file__).read_text(encoding="utf-8")
    passed = sorted(backend_matches) == allowed_backend and not present and order_token not in test_text
    return show("No fake price generation or execution enablement added", passed, ", ".join(backend_matches + present))


def main() -> int:
    print("Phase 20 Day 4 XAUUSD Tick Recovery Verification")
    print("=" * 78)
    checks = [
        verify_doc_exists(),
        verify_direct_tick_success_case(),
        verify_symbol_info_fallback_success_case(),
        verify_unavailable_tick_remains_blocked(),
        verify_tick_failure_debounce_uses_last_good_quote(),
        verify_source_contains_recovery_logic(),
        verify_live_route_shape(),
        verify_no_fake_price_or_execution(),
    ]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
