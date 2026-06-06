import sys
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


REQUIRED_FILES = [
    "backend/demo_validation/nifty50_demo_validation_service.py",
    "backend/api/demo_validation_routes.py",
    "docs/phase14-day5-nifty50-demo-signal-validation.md",
]

NIFTY50_ROUTES = {
    "/demo-validation/nifty50/status",
    "/demo-validation/nifty50/run",
    "/demo-validation/nifty50/latest",
    "/demo-validation/nifty50/history",
}

PREVIOUS_DEMO_VALIDATION_ROUTES = {
    "/demo-validation/xauusd/status",
    "/demo-validation/xauusd/run",
    "/demo-validation/xauusd/latest",
    "/demo-validation/xauusd/history",
    "/demo-validation/eurusd/status",
    "/demo-validation/eurusd/run",
    "/demo-validation/eurusd/latest",
    "/demo-validation/eurusd/history",
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
        if key == "preview_only" and value is not True:
            return False
    return True


def verify_files() -> bool:
    missing = [path for path in REQUIRED_FILES if not (PROJECT_ROOT / path).is_file()]
    return show("NIFTY50 demo validation service, routes, and docs exist", not missing, ", ".join(missing))


def verify_nifty50_routes_and_run() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        route_paths = {route.path for route in app.routes if hasattr(route, "methods")}
        missing_routes = NIFTY50_ROUTES - route_paths
        status = client.get("/demo-validation/nifty50/status")
        run = client.post("/demo-validation/nifty50/run")
        latest = client.get("/demo-validation/nifty50/latest")
        history = client.get("/demo-validation/nifty50/history")
        payload = run.json()
        passed = (
            not missing_routes
            and status.status_code == 200
            and run.status_code == 200
            and latest.status_code == 200
            and history.status_code == 200
            and payload["symbol"] == "NIFTY50"
            and payload["environment"] == "DEMO_SIMULATION"
            and payload["market_data_checked"] is True
            and payload["strategy_checked"] is True
            and payload["risk_checked"] is True
            and payload["execution_preview_checked"] is True
            and payload["execution_status"]["preview_only"] is True
            and payload["execution_status"]["execution_ready"] is False
            and payload["execution_status"]["execution_allowed"] is False
            and payload["analytics_check"]["nifty50_in_symbols"] is True
            and payload["analytics_check"]["nifty50_in_strategy_performance"] is True
            and payload["analytics_check"]["nifty50_in_executive_instruments"] is True
            and payload["analytics_check"]["nifty50_live_ready"] is False
            and payload["status"] in {"PASS", "WARNING"}
            and isinstance(history.json(), list)
            and len(history.json()) >= 1
            and all(safety_ok(item) for item in [status.json(), payload, latest.json(), history.json()])
        )
        return show("NIFTY50 demo validation routes run safely", passed, ", ".join(sorted(missing_routes)))
    except Exception as exc:
        return show("NIFTY50 demo validation routes run safely", False, str(exc))


def verify_previous_demo_validation_routes() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        route_paths = {route.path for route in app.routes if hasattr(route, "methods")}
        missing_routes = PREVIOUS_DEMO_VALIDATION_ROUTES - route_paths
        checks = [
            client.get("/demo-validation/xauusd/status"),
            client.get("/demo-validation/eurusd/status"),
        ]
        passed = (
            not missing_routes
            and all(response.status_code == 200 for response in checks)
            and all(safety_ok(response.json()) for response in checks)
        )
        return show("XAUUSD and EURUSD demo validation routes are preserved", passed, ", ".join(sorted(missing_routes)))
    except Exception as exc:
        return show("XAUUSD and EURUSD demo validation routes are preserved", False, str(exc))


def verify_nifty50_api_safety_routes() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        execution_status = client.get("/nifty50/execution/status")
        readiness = client.get("/nifty50/readiness")
        market_status = client.get("/nifty50/market-data/status")
        passed = (
            execution_status.status_code == 200
            and readiness.status_code == 200
            and market_status.status_code == 200
            and execution_status.json()["preview_only"] is True
            and execution_status.json()["execution_allowed"] is False
            and execution_status.json()["live_execution_enabled"] is False
            and execution_status.json()["broker_execution_enabled"] is False
            and safety_ok(execution_status.json())
            and safety_ok(readiness.json())
            and safety_ok(market_status.json())
        )
        return show("NIFTY50 remains preview-only and simulation-only", passed)
    except Exception as exc:
        return show("NIFTY50 remains preview-only and simulation-only", False, str(exc))


def verify_no_external_broker_calls() -> bool:
    forbidden_tokens = [
        "requests.",
        "httpx.",
        "aiohttp",
        "urllib.request",
        "kiteconnect",
        "smartapi",
        "dhanhq",
        "fyers_apiv3",
        "upstox_client",
        "broker_api_key",
    ]
    files = [
        PROJECT_ROOT / "backend" / "demo_validation" / "nifty50_demo_validation_service.py",
        PROJECT_ROOT / "backend" / "api" / "demo_validation_routes.py",
    ]
    matches: list[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for token in forbidden_tokens:
            if token in text:
                matches.append(f"{path.relative_to(PROJECT_ROOT).as_posix()}::{token}")
    return show("No external broker/API calls added for validation", not matches, ", ".join(matches))


def verify_no_order_send_added() -> bool:
    try:
        token = "mt5." + "order_send"
        order_matches = []
        for path in (PROJECT_ROOT / "backend").rglob("*.py"):
            if token in path.read_text(encoding="utf-8", errors="ignore"):
                order_matches.append(path.relative_to(PROJECT_ROOT).as_posix())
        return show(
            "No new mt5 order execution path was added",
            order_matches == ["backend/demo_execution/mt5_demo_executor.py"],
            ", ".join(order_matches),
        )
    except Exception as exc:
        return show("No new mt5 order execution path was added", False, str(exc))


def main() -> int:
    print("Phase 14 Day 5 NIFTY50 Demo Signal Verification")
    print("=" * 78)
    checks = [
        verify_files(),
        verify_nifty50_routes_and_run(),
        verify_previous_demo_validation_routes(),
        verify_nifty50_api_safety_routes(),
        verify_no_external_broker_calls(),
        verify_no_order_send_added(),
    ]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
