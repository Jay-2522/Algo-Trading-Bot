import sys
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


REQUIRED_FILES = [
    "backend/demo_validation/eurusd_demo_validation_service.py",
    "backend/api/demo_validation_routes.py",
    "docs/phase14-day4-eurusd-demo-signal-validation.md",
]

EURUSD_ROUTES = {
    "/demo-validation/eurusd/status",
    "/demo-validation/eurusd/run",
    "/demo-validation/eurusd/latest",
    "/demo-validation/eurusd/history",
}

XAUUSD_ROUTES = {
    "/demo-validation/xauusd/status",
    "/demo-validation/xauusd/run",
    "/demo-validation/xauusd/latest",
    "/demo-validation/xauusd/history",
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
        if key == "simulation_only" and value is not True:
            return False
        if key in {"live_execution_enabled", "broker_execution_enabled", "execution_allowed"} and value is not False:
            return False
    return True


def verify_files() -> bool:
    missing = [path for path in REQUIRED_FILES if not (PROJECT_ROOT / path).is_file()]
    return show("EURUSD demo validation service, routes, and docs exist", not missing, ", ".join(missing))


def verify_eurusd_routes_and_run() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        route_paths = {route.path for route in app.routes if hasattr(route, "methods")}
        missing_routes = EURUSD_ROUTES - route_paths
        status = client.get("/demo-validation/eurusd/status")
        run = client.post("/demo-validation/eurusd/run")
        latest = client.get("/demo-validation/eurusd/latest")
        history = client.get("/demo-validation/eurusd/history")
        run_payload = run.json()
        passed = (
            not missing_routes
            and status.status_code == 200
            and run.status_code == 200
            and latest.status_code == 200
            and history.status_code == 200
            and run_payload["symbol"] == "EURUSD"
            and run_payload["environment"] == "DEMO"
            and run_payload["signal_generated"] is True
            and run_payload["risk_checked"] is True
            and run_payload["risk_approved"] is False
            and run_payload["bridge_checked"] is True
            and run_payload["bridge_decision"]["eligible"] is False
            and run_payload["bridge_decision"]["queue_preview_created"] is False
            and run_payload["analytics_check"]["eurusd_in_symbols"] is True
            and run_payload["analytics_check"]["eurusd_in_strategy_performance"] is True
            and run_payload["analytics_check"]["eurusd_in_executive_instruments"] is True
            and run_payload["status"] in {"PASS", "WARNING"}
            and isinstance(history.json(), list)
            and len(history.json()) >= 1
            and all(safety_ok(payload) for payload in [status.json(), run_payload, latest.json(), history.json()])
        )
        return show("EURUSD demo validation routes run safely", passed, ", ".join(sorted(missing_routes)))
    except Exception as exc:
        return show("EURUSD demo validation routes run safely", False, str(exc))


def verify_xauusd_regression() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        route_paths = {route.path for route in app.routes if hasattr(route, "methods")}
        missing_routes = XAUUSD_ROUTES - route_paths
        status = client.get("/demo-validation/xauusd/status")
        latest = client.get("/demo-validation/xauusd/latest")
        run = client.post("/demo-validation/xauusd/run")
        history = client.get("/demo-validation/xauusd/history")
        passed = (
            not missing_routes
            and status.status_code == 200
            and latest.status_code == 200
            and run.status_code == 200
            and history.status_code == 200
            and run.json()["symbol"] == "XAUUSD"
            and run.json()["bridge_decision"]["eligible"] is False
            and all(safety_ok(payload) for payload in [status.json(), latest.json(), run.json(), history.json()])
        )
        return show("XAUUSD demo validation routes still work", passed, ", ".join(sorted(missing_routes)))
    except Exception as exc:
        return show("XAUUSD demo validation routes still work", False, str(exc))


def verify_no_execution() -> bool:
    try:
        token = "mt5." + "order_send"
        order_matches = []
        for path in (PROJECT_ROOT / "backend").rglob("*.py"):
            if token in path.read_text(encoding="utf-8", errors="ignore"):
                order_matches.append(path.relative_to(PROJECT_ROOT).as_posix())
        return show(
            "No order execution path was added",
            order_matches == ["backend/demo_execution/mt5_demo_executor.py"],
            ", ".join(order_matches),
        )
    except Exception as exc:
        return show("No order execution path was added", False, str(exc))


def main() -> int:
    print("Phase 14 Day 4 EURUSD Demo Signal Verification")
    print("=" * 74)
    checks = [
        verify_files(),
        verify_eurusd_routes_and_run(),
        verify_xauusd_regression(),
        verify_no_execution(),
    ]
    print("=" * 74)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
