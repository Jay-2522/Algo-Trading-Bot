import sys
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

REQUIRED_FILES = [
    "backend/mt5_demo/demo_order_authorization_models.py",
    "backend/mt5_demo/demo_order_authorization_service.py",
    "docs/phase16-day1-demo-order-authorization.md",
]

ROUTES = {
    "/mt5-demo/demo-authorization/status",
    "/mt5-demo/demo-authorization/request",
    "/mt5-demo/demo-authorization/revoke",
    "/mt5-demo/demo-authorization/checklist",
}

VALID_REQUEST = {
    "environment": "DEMO",
    "manual_confirmation": True,
    "acknowledge_no_live_trading": True,
    "acknowledge_demo_only": True,
    "max_demo_lot": 0.01,
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
        if key in {"live_execution_enabled", "broker_execution_enabled", "execution_allowed", "execution_triggered"} and value is True:
            return False
    return True


def verify_files() -> bool:
    missing = [path for path in REQUIRED_FILES if not (PROJECT_ROOT / path).is_file()]
    return show("Authorization models, service, and docs exist", not missing, ", ".join(missing))


def verify_routes_and_authorization() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        paths = {route.path for route in app.routes if hasattr(route, "methods")}
        missing = sorted(ROUTES - paths)
        default = client.get("/mt5-demo/demo-authorization/status")
        invalid = client.post("/mt5-demo/demo-authorization/request", json={"environment": "LIVE"})
        valid = client.post("/mt5-demo/demo-authorization/request", json=VALID_REQUEST)
        checklist = client.get("/mt5-demo/demo-authorization/checklist")
        revoke = client.post("/mt5-demo/demo-authorization/revoke")
        payloads = [default.json(), invalid.json(), valid.json(), checklist.json(), revoke.json()]
        passed = (
            not missing
            and all(response.status_code == 200 for response in [default, invalid, valid, checklist, revoke])
            and default.json()["demo_order_testing_enabled"] is False
            and default.json()["live_execution_enabled"] is False
            and default.json()["broker_execution_enabled"] is False
            and default.json()["execution_allowed"] is False
            and default.json()["status"] == "LOCKED"
            and invalid.json()["authorization_granted"] is False
            and invalid.json()["status"] == "LOCKED"
            and valid.json()["authorization_granted"] is True
            and valid.json()["status"] == "READY_FOR_DEMO_ORDER_TESTING"
            and valid.json()["execution_allowed"] is False
            and valid.json()["live_execution_enabled"] is False
            and valid.json()["broker_execution_enabled"] is False
            and len(checklist.json()["items"]) == 10
            and revoke.json()["status"] == "LOCKED"
            and revoke.json()["demo_order_testing_enabled"] is False
            and all(safety_ok(payload) for payload in payloads)
        )
        return show("Authorization routes enforce locked safety", passed, ", ".join(missing))
    except Exception as exc:
        return show("Authorization routes enforce locked safety", False, str(exc))


def verify_no_order_send_added() -> bool:
    token = "mt5." + "order_send"
    matches = [
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in (PROJECT_ROOT / "backend").rglob("*.py")
        if token in path.read_text(encoding="utf-8", errors="ignore")
    ]
    return show("No new mt5 order execution path was added", matches == ["backend/demo_execution/mt5_demo_executor.py"], ", ".join(matches))


def main() -> int:
    print("Phase 16 Day 1 Demo Order Authorization Verification")
    print("=" * 78)
    checks = [verify_files(), verify_routes_and_authorization(), verify_no_order_send_added()]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
