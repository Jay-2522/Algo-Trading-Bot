import sys
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


REQUIRED_FILES = [
    "backend/mt5_demo/mt5_demo_service.py",
    "backend/api/mt5_demo_routes.py",
    "docs/phase14-day2-mt5-demo-integration.md",
]

REQUIRED_GET_ROUTES = {
    "/mt5-demo/status",
    "/mt5-demo/account",
    "/mt5-demo/symbols",
    "/mt5-demo/health",
    "/mt5-demo/market-watch",
}

BLOCKED_ACTION_ROUTES = [
    "/mt5-demo/order-send",
    "/mt5-demo/position-open",
    "/mt5-demo/market-buy",
    "/mt5-demo/market-sell",
]


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
    return show("MT5 demo service, routes, and docs exist", not missing, ", ".join(missing))


def verify_routes_and_payloads() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        route_paths = {route.path for route in app.routes if hasattr(route, "methods")}
        missing_routes = REQUIRED_GET_ROUTES - route_paths
        responses = {route: client.get(route) for route in REQUIRED_GET_ROUTES}
        payloads = {route: response.json() for route, response in responses.items()}
        market_watch = payloads["/mt5-demo/market-watch"]
        watched_symbols = {item.get("symbol") for item in market_watch.get("symbols", [])}
        passed = (
            not missing_routes
            and all(response.status_code == 200 for response in responses.values())
            and payloads["/mt5-demo/status"]["environment"] == "DEMO"
            and payloads["/mt5-demo/status"]["status"] in {"CONNECTED", "NOT_CONNECTED"}
            and {"XAUUSD", "EURUSD"} <= watched_symbols
            and all(safety_ok(payload) for payload in payloads.values())
        )
        return show("MT5 demo read-only routes work", passed, ", ".join(sorted(missing_routes)))
    except Exception as exc:
        return show("MT5 demo read-only routes work", False, str(exc))


def verify_safety_locks() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        payloads = []
        for route in BLOCKED_ACTION_ROUTES:
            response = client.post(route)
            if response.status_code != 200:
                return show("MT5 demo action safety locks active", False, f"{route} status={response.status_code}")
            payload = response.json()
            payloads.append(payload)
            if payload.get("allowed") is not False or payload.get("reason") != "PHASE_14_DEMO_ONLY":
                return show("MT5 demo action safety locks active", False, f"{route} payload={payload}")

        token = "mt5." + "order_send"
        matches = []
        for path in (PROJECT_ROOT / "backend").rglob("*.py"):
            if token in path.read_text(encoding="utf-8", errors="ignore"):
                matches.append(path.relative_to(PROJECT_ROOT).as_posix())

        passed = all(safety_ok(payload) for payload in payloads) and matches == ["backend/demo_execution/mt5_demo_executor.py"]
        return show("MT5 demo action safety locks active", passed, ", ".join(matches))
    except Exception as exc:
        return show("MT5 demo action safety locks active", False, str(exc))


def main() -> int:
    print("Phase 14 Day 2 MT5 Demo Verification")
    print("=" * 70)
    checks = [
        verify_files(),
        verify_routes_and_payloads(),
        verify_safety_locks(),
    ]
    print("=" * 70)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
