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


def stub_approved_state() -> None:
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
    mt5_demo_routes.demo_approval_workflow_service.get_latest = lambda: {
        "approved_for_future_demo_order": True,
        "approved_trade_count": 1,
        "execution_allowed": False,
        "live_execution_enabled": False,
        "broker_execution_enabled": False,
    }
    mt5_demo_routes.demo_final_approval_service.get_latest_approval = lambda: {
        "approved_for_future_demo_order": True,
        "approved_trade_count": 1,
        "execution_allowed": False,
        "live_execution_enabled": False,
        "broker_execution_enabled": False,
    }
    mt5_demo_routes.demo_order_dry_run_service.get_latest = lambda: {"validation_passed": True}
    mt5_demo_routes.demo_order_preflight_service.get_latest = lambda: {"validation_passed": True}
    mt5_demo_routes.demo_execution_simulator_service.get_latest = lambda: {"simulation_passed": True}
    mt5_demo_routes.demo_execution_readiness_service.get_latest_audit = lambda: {"overall_status": "READY"}


def verify_files() -> bool:
    files = [
        "backend/mt5_demo/guarded_demo_order_sender_service.py",
        "docs/phase17-day2-guarded-runtime-demo-sender.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    return show("Guarded runtime sender docs exist", not missing, ", ".join(missing))


def verify_routes_and_rejections() -> bool:
    try:
        from backend.main import app

        stub_approved_state()
        client = TestClient(app)
        paths = {route.path for route in app.routes if hasattr(route, "methods")}
        missing = sorted(ROUTES - paths)
        status = client.get("/mt5-demo/guarded-demo-order/status")
        send_without_flag = client.post("/mt5-demo/guarded-demo-order/send", json=VALID_GUARDED)
        invalid_lot = client.post("/mt5-demo/guarded-demo-order/prepare", json={**VALID_GUARDED, "lot": 0.02})
        xauusd = client.post("/mt5-demo/guarded-demo-order/prepare", json={**VALID_GUARDED, "symbol": "XAUUSD"})
        missing_confirmation = client.post("/mt5-demo/guarded-demo-order/prepare", json={**VALID_GUARDED, "manual_confirmation": False})
        payloads = [status.json(), send_without_flag.json(), invalid_lot.json(), xauusd.json(), missing_confirmation.json()]
        passed = (
            not missing
            and all(response.status_code == 200 for response in [status, send_without_flag, invalid_lot, xauusd, missing_confirmation])
            and send_without_flag.json()["status"] == "PREPARED_BUT_NOT_SENT"
            and send_without_flag.json()["mt5_order_sent"] is False
            and send_without_flag.json()["demo_order_attempted"] is False
            and "LOT_MUST_BE_EXACTLY_0_01" in invalid_lot.json()["blockers"]
            and "RUNTIME_SYMBOL_NOT_ENABLED" in xauusd.json()["blockers"]
            and "MANUAL_CONFIRMATION_REQUIRED" in missing_confirmation.json()["blockers"]
            and status.json()["live_execution_enabled"] is False
            and status.json()["broker_execution_enabled"] is False
            and all(safety_ok(payload) for payload in payloads)
        )
        return show("Guarded runtime routes reject without sending", passed, ", ".join(missing))
    except Exception as exc:
        return show("Guarded runtime routes reject without sending", False, str(exc))


def verify_scoped_order_send() -> bool:
    token = "mt5." + "order_send"
    allowed = [
        "backend/demo_execution/mt5_demo_executor.py",
        "backend/mt5_demo/guarded_demo_order_sender_service.py",
    ]
    matches = [
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in (PROJECT_ROOT / "backend").rglob("*.py")
        if token in path.read_text(encoding="utf-8", errors="ignore")
    ]
    service_text = (PROJECT_ROOT / "backend/mt5_demo/guarded_demo_order_sender_service.py").read_text(encoding="utf-8")
    scoped = (
        "def _send_to_mt5" in service_text
        and "mt5.order_send(order_request)" in service_text
        and "execute_single_demo_order_now" in service_text
        and "DEMO" in service_text
        and "RUNTIME_SYMBOL_NOT_ENABLED" in service_text
    )
    return show("mt5.order_send is scoped to guarded sender", sorted(matches) == allowed and scoped, ", ".join(matches))


def main() -> int:
    print("Phase 17 Day 2 Guarded Runtime Sender Verification")
    print("=" * 78)
    checks = [verify_files(), verify_routes_and_rejections(), verify_scoped_order_send()]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
