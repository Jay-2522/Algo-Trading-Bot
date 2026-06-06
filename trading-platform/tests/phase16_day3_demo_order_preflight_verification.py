import sys
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

REQUIRED_FILES = [
    "backend/mt5_demo/demo_order_preflight_models.py",
    "backend/mt5_demo/demo_order_preflight_service.py",
    "docs/phase16-day3-demo-order-preflight.md",
]

ROUTES = {
    "/mt5-demo/preflight/status",
    "/mt5-demo/preflight/run",
    "/mt5-demo/preflight/latest",
    "/mt5-demo/preflight/history",
}

AUTHORIZATION_REQUEST = {
    "environment": "DEMO",
    "manual_confirmation": True,
    "acknowledge_no_live_trading": True,
    "acknowledge_demo_only": True,
    "max_demo_lot": 0.01,
}

DRY_RUN_REQUEST = {
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
        if key in {"execution_allowed", "live_execution_enabled", "broker_execution_enabled"} and value is True:
            return False
    return True


def fake_spread(symbol: str) -> dict[str, Any]:
    return {
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


def verify_files() -> bool:
    missing = [path for path in REQUIRED_FILES if not (PROJECT_ROOT / path).is_file()]
    return show("Preflight models, service, and docs exist", not missing, ", ".join(missing))


def verify_routes_and_preflight() -> bool:
    try:
        from backend.main import app
        from backend.api import mt5_demo_routes

        mt5_demo_routes.demo_order_preflight_service.market_data_service.get_symbol_spread = fake_spread
        client = TestClient(app)
        paths = {route.path for route in app.routes if hasattr(route, "methods")}
        missing = sorted(ROUTES - paths)

        client.post("/mt5-demo/demo-authorization/revoke")
        locked = client.post("/mt5-demo/preflight/run", json=DRY_RUN_REQUEST)
        client.post("/mt5-demo/demo-authorization/request", json=AUTHORIZATION_REQUEST)
        dry_run = client.post("/mt5-demo/demo-order-dry-run/create", json=DRY_RUN_REQUEST).json()
        valid_request = {
            "dry_run_id": dry_run["dry_run_id"],
            "symbol": "EURUSD",
            "action": "BUY",
            "lot": 0.01,
            "entry_price": 1.12345,
            "stop_loss": 1.12,
            "take_profit": 1.13,
        }
        invalid_cases = [
            ("invalid symbol", {**valid_request, "symbol": "GBPUSD"}, "Invalid symbol."),
            ("invalid action", {**valid_request, "action": "HOLD"}, "Invalid action."),
            ("lot above max", {**valid_request, "lot": 0.02}, "Lot must be greater"),
            ("missing stop loss", {key: value for key, value in valid_request.items() if key != "stop_loss"}, "stop_loss is required."),
            ("missing take profit", {key: value for key, value in valid_request.items() if key != "take_profit"}, "take_profit is required."),
        ]
        invalid_results = [(name, client.post("/mt5-demo/preflight/run", json=payload), expected) for name, payload, expected in invalid_cases]
        valid = client.post("/mt5-demo/preflight/run", json=valid_request)
        status = client.get("/mt5-demo/preflight/status")
        latest = client.get("/mt5-demo/preflight/latest")
        history = client.get("/mt5-demo/preflight/history")
        payloads = [locked.json(), valid.json(), status.json(), latest.json(), history.json()] + [response.json() for _, response, _ in invalid_results]
        invalid_passed = all(
            response.status_code == 200
            and response.json()["validation_passed"] is False
            and any(expected in reason for reason in response.json()["rejection_reasons"])
            for _, response, expected in invalid_results
        )
        passed = (
            not missing
            and all(response.status_code == 200 for response in [locked, valid, status, latest, history])
            and locked.json()["validation_passed"] is False
            and any("authorization" in reason.lower() for reason in locked.json()["rejection_reasons"])
            and invalid_passed
            and valid.json()["validation_passed"] is True
            and valid.json()["would_be_allowed_in_demo"] is True
            and valid.json()["execution_allowed"] is False
            and valid.json()["live_execution_enabled"] is False
            and valid.json()["broker_execution_enabled"] is False
            and valid.json()["symbol_check"] is True
            and valid.json()["action_check"] is True
            and valid.json()["lot_check"] is True
            and valid.json()["risk_check"] is True
            and valid.json()["authorization_check"] is True
            and valid.json()["execution_gate_check"] is True
            and valid.json()["spread_check"] is True
            and valid.json()["market_data_check"] is True
            and latest.json()["preflight_id"] == valid.json()["preflight_id"]
            and isinstance(history.json(), list)
            and all(safety_ok(payload) for payload in payloads)
        )
        return show("Preflight routes validate readiness safely", passed, ", ".join(missing))
    except Exception as exc:
        return show("Preflight routes validate readiness safely", False, str(exc))


def verify_no_order_send_added() -> bool:
    token = "mt5." + "order_send"
    matches = [
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in (PROJECT_ROOT / "backend").rglob("*.py")
        if token in path.read_text(encoding="utf-8", errors="ignore")
    ]
    return show("No new mt5 order execution path was added", matches == ["backend/demo_execution/mt5_demo_executor.py"], ", ".join(matches))


def main() -> int:
    print("Phase 16 Day 3 Demo Order Preflight Verification")
    print("=" * 78)
    checks = [verify_files(), verify_routes_and_preflight(), verify_no_order_send_added()]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
