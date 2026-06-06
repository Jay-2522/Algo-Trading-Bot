import sys
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

ROUTES = {
    "/mt5-demo/guarded-demo-order/status",
    "/mt5-demo/guarded-demo-order/prepare",
    "/mt5-demo/guarded-demo-order/send",
    "/mt5-demo/guarded-demo-order/latest",
    "/mt5-demo/guarded-demo-order/history",
}

VALID_WORKFLOW = {
    "environment": "DEMO",
    "symbol": "EURUSD",
    "action": "BUY",
    "lot": 0.01,
    "entry_price": 1.12345,
    "stop_loss": 1.12,
    "take_profit": 1.13,
    "manual_confirmation": True,
    "acknowledge_no_live_trading": True,
    "acknowledge_demo_only": True,
    "acknowledge_no_order_placement_today": True,
}

VALID_GUARDED = {
    "environment": "DEMO",
    "symbol": "EURUSD",
    "action": "BUY",
    "lot": 0.01,
    "entry_price": 1.12345,
    "stop_loss": 1.12,
    "take_profit": 1.13,
    "manual_confirmation": True,
    "acknowledge_demo_only": True,
    "acknowledge_no_live_trading": True,
    "acknowledge_single_trade_only": True,
}


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def walk(payload: Any):
    if isinstance(payload, dict):
        for key, value in payload.items():
            yield key, value
            yield from walk(value)
    elif isinstance(payload, list):
        for item in payload:
            yield from walk(item)


def safety_ok(payload: Any) -> bool:
    for key, value in walk(payload):
        if key in {"mt5_order_sent", "live_order_attempted", "live_execution_enabled", "broker_execution_enabled"} and value is True:
            return False
    return True


def install_read_only_environment_stubs() -> None:
    from backend.api import mt5_demo_routes

    mt5_demo_routes.service.get_status = lambda: {
        "status": "CONNECTED",
        "environment": "DEMO",
        "account_type": "DEMO",
        "simulation_only": True,
        "live_execution_enabled": False,
        "broker_execution_enabled": False,
        "execution_allowed": False,
    }
    mt5_demo_routes.market_data_service.get_market_data_status = lambda: {
        "status": "READY",
        "simulation_only": True,
        "live_execution_enabled": False,
        "broker_execution_enabled": False,
        "execution_allowed": False,
    }
    mt5_demo_routes.market_data_service.get_symbol_spread = lambda symbol: {
        "symbol": symbol,
        "bid": 1.1234,
        "ask": 1.12345,
        "spread": 0.00005,
        "status": "OK",
        "simulation_only": True,
        "live_execution_enabled": False,
        "broker_execution_enabled": False,
        "execution_allowed": False,
    }
    mt5_demo_routes.historical_backfill_service.summarize_backfill = lambda symbol, timeframe: {
        "symbol": symbol,
        "timeframe": timeframe,
        "returned_count": 500,
        "validation": {"valid": True, "stale": False, "warnings": []},
        "status": "OK",
        "simulation_only": True,
        "live_execution_enabled": False,
        "broker_execution_enabled": False,
        "execution_allowed": False,
    }
    mt5_demo_routes.strategy_feed_adapter.build_strategy_feed = lambda symbol: {
        "symbol": symbol,
        "feed_ready": True,
        "status": "READY",
        "simulation_only": True,
        "live_execution_enabled": False,
        "broker_execution_enabled": False,
        "execution_allowed": False,
    }


def verify_files() -> bool:
    files = [
        "backend/mt5_demo/guarded_demo_order_sender_service.py",
        "docs/phase17-day1-guarded-demo-order-sender.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    return show("Guarded sender service and docs exist", not missing, ", ".join(missing))


def verify_routes_and_guard() -> bool:
    try:
        from backend.main import app

        install_read_only_environment_stubs()
        client = TestClient(app)
        paths = {route.path for route in app.routes if hasattr(route, "methods")}
        missing = sorted(ROUTES - paths)
        workflow = client.post("/mt5-demo/demo-approval-workflow/run", json=VALID_WORKFLOW)
        status = client.get("/mt5-demo/guarded-demo-order/status")
        prepare = client.post("/mt5-demo/guarded-demo-order/prepare", json=VALID_GUARDED)
        send_without_flag = client.post("/mt5-demo/guarded-demo-order/send", json=VALID_GUARDED)
        invalid_lot = client.post("/mt5-demo/guarded-demo-order/prepare", json={**VALID_GUARDED, "lot": 0.02})
        invalid_symbol = client.post("/mt5-demo/guarded-demo-order/prepare", json={**VALID_GUARDED, "symbol": "GBPUSD"})
        missing_confirmation = client.post("/mt5-demo/guarded-demo-order/prepare", json={**VALID_GUARDED, "manual_confirmation": False})
        latest = client.get("/mt5-demo/guarded-demo-order/latest")
        history = client.get("/mt5-demo/guarded-demo-order/history")
        payloads = [
            status.json(),
            prepare.json(),
            send_without_flag.json(),
            invalid_lot.json(),
            invalid_symbol.json(),
            missing_confirmation.json(),
            latest.json(),
            history.json(),
        ]
        passed = (
            not missing
            and workflow.status_code == 200
            and workflow.json().get("approved_for_future_demo_order") is True
            and all(response.status_code == 200 for response in [status, prepare, send_without_flag, invalid_lot, invalid_symbol, missing_confirmation, latest, history])
            and status.json()["single_trade_limit"] == 1
            and prepare.json()["status"] == "PREPARED_BUT_NOT_SENT"
            and prepare.json()["mt5_order_sent"] is False
            and prepare.json()["demo_order_attempted"] is False
            and send_without_flag.json()["status"] == "PREPARED_BUT_NOT_SENT"
            and send_without_flag.json()["mt5_order_sent"] is False
            and send_without_flag.json()["demo_order_attempted"] is False
            and "LOT_EXCEEDS_MAX_DEMO_LOT" in invalid_lot.json()["blockers"]
            and "INVALID_SYMBOL" in invalid_symbol.json()["blockers"]
            and "MANUAL_CONFIRMATION_REQUIRED" in missing_confirmation.json()["blockers"]
            and all(item.get("live_order_attempted") is not True for item in [prepare.json(), send_without_flag.json(), invalid_lot.json(), invalid_symbol.json(), missing_confirmation.json()])
            and isinstance(history.json(), list)
            and all(safety_ok(payload) for payload in payloads)
        )
        return show("Guarded sender routes prepare without sending", passed, ", ".join(missing))
    except Exception as exc:
        return show("Guarded sender routes prepare without sending", False, str(exc))


def verify_no_unrestricted_order_send() -> bool:
    token = "mt5." + "order_send"
    matches = [
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in (PROJECT_ROOT / "backend").rglob("*.py")
        if token in path.read_text(encoding="utf-8", errors="ignore")
    ]
    return show("No unrestricted mt5 order execution path was added", matches == ["backend/demo_execution/mt5_demo_executor.py"], ", ".join(matches))


def main() -> int:
    print("Phase 17 Day 1 Guarded Demo Order Sender Verification")
    print("=" * 78)
    checks = [verify_files(), verify_routes_and_guard(), verify_no_unrestricted_order_send()]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
