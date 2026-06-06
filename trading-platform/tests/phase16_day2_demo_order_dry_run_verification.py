import sys
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

REQUIRED_FILES = [
    "backend/mt5_demo/demo_order_dry_run_models.py",
    "backend/mt5_demo/demo_order_dry_run_service.py",
    "docs/phase16-day2-demo-order-dry-run-builder.md",
]

ROUTES = {
    "/mt5-demo/demo-order-dry-run/status",
    "/mt5-demo/demo-order-dry-run/create",
    "/mt5-demo/demo-order-dry-run/latest",
    "/mt5-demo/demo-order-dry-run/history",
}

AUTHORIZATION_REQUEST = {
    "environment": "DEMO",
    "manual_confirmation": True,
    "acknowledge_no_live_trading": True,
    "acknowledge_demo_only": True,
    "max_demo_lot": 0.01,
}

VALID_DRY_RUN = {
    "symbol": "EURUSD",
    "action": "BUY",
    "lot": 0.01,
    "entry_price": 1.12345,
    "stop_loss": 1.12,
    "take_profit": 1.13,
    "risk_decision_id": "risk-demo-approved-preview",
    "gate_decision_id": "gate-demo-ready-preview",
    "manual_confirmation": True,
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
        if key in {"would_send_to_mt5", "mt5_order_sent", "execution_allowed", "live_execution_enabled", "broker_execution_enabled"} and value is True:
            return False
    return True


def verify_files() -> bool:
    missing = [path for path in REQUIRED_FILES if not (PROJECT_ROOT / path).is_file()]
    return show("Dry-run models, service, and docs exist", not missing, ", ".join(missing))


def verify_routes_and_dry_runs() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        client.post("/mt5-demo/demo-authorization/revoke")
        paths = {route.path for route in app.routes if hasattr(route, "methods")}
        missing = sorted(ROUTES - paths)
        status_locked = client.get("/mt5-demo/demo-order-dry-run/status")
        locked_attempt = client.post("/mt5-demo/demo-order-dry-run/create", json=VALID_DRY_RUN)
        client.post("/mt5-demo/demo-authorization/request", json=AUTHORIZATION_REQUEST)

        invalid_cases = [
            ("unsupported symbol", {**VALID_DRY_RUN, "symbol": "GBPUSD"}, "Unsupported symbol"),
            ("unsupported action", {**VALID_DRY_RUN, "action": "HOLD"}, "Unsupported action"),
            ("lot above max", {**VALID_DRY_RUN, "lot": 0.02}, "Lot exceeds"),
            ("missing stop loss", {key: value for key, value in VALID_DRY_RUN.items() if key != "stop_loss"}, "stop_loss is required"),
            ("missing take profit", {key: value for key, value in VALID_DRY_RUN.items() if key != "take_profit"}, "take_profit is required"),
            ("missing manual confirmation", {**VALID_DRY_RUN, "manual_confirmation": False}, "manual_confirmation must be true"),
        ]
        invalid_results = [
            (name, client.post("/mt5-demo/demo-order-dry-run/create", json=payload), expected)
            for name, payload, expected in invalid_cases
        ]
        valid = client.post("/mt5-demo/demo-order-dry-run/create", json=VALID_DRY_RUN)
        latest = client.get("/mt5-demo/demo-order-dry-run/latest")
        history = client.get("/mt5-demo/demo-order-dry-run/history")
        payloads = [status_locked.json(), locked_attempt.json(), valid.json(), latest.json(), history.json()] + [response.json() for _, response, _ in invalid_results]

        invalid_passed = all(
            response.status_code == 200
            and response.json()["validation_passed"] is False
            and any(expected in reason for reason in response.json()["rejection_reasons"])
            for _, response, expected in invalid_results
        )
        passed = (
            not missing
            and all(response.status_code == 200 for response in [status_locked, locked_attempt, valid, latest, history])
            and status_locked.json()["status"] == "DRY_RUN_LOCKED"
            and locked_attempt.json()["validation_passed"] is False
            and any("authorization is locked" in reason.lower() for reason in locked_attempt.json()["rejection_reasons"])
            and invalid_passed
            and valid.json()["validation_passed"] is True
            and valid.json()["order_payload_preview"]["symbol"] == "EURUSD"
            and valid.json()["order_payload_preview"]["type"] == "BUY"
            and valid.json()["order_payload_preview"]["volume"] == 0.01
            and valid.json()["would_send_to_mt5"] is False
            and valid.json()["mt5_order_sent"] is False
            and valid.json()["execution_allowed"] is False
            and valid.json()["live_execution_enabled"] is False
            and valid.json()["broker_execution_enabled"] is False
            and latest.json()["dry_run_id"] == valid.json()["dry_run_id"]
            and isinstance(history.json(), list)
            and len(history.json()) >= 1
            and all(safety_ok(payload) for payload in payloads)
        )
        detail = ", ".join(missing + [name for name, response, _ in invalid_results if response.json().get("validation_passed") is not False])
        return show("Dry-run routes validate previews safely", passed, detail)
    except Exception as exc:
        return show("Dry-run routes validate previews safely", False, str(exc))


def verify_no_order_send_added() -> bool:
    token = "mt5." + "order_send"
    matches = [
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in (PROJECT_ROOT / "backend").rglob("*.py")
        if token in path.read_text(encoding="utf-8", errors="ignore")
    ]
    return show("No new mt5 order execution path was added", matches == ["backend/demo_execution/mt5_demo_executor.py"], ", ".join(matches))


def main() -> int:
    print("Phase 16 Day 2 Demo Order Dry-Run Verification")
    print("=" * 78)
    checks = [verify_files(), verify_routes_and_dry_runs(), verify_no_order_send_added()]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
