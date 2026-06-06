import sys
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


REQUIRED_FILES = [
    "backend/demo_environment/demo_environment_service.py",
    "backend/api/demo_environment_routes.py",
    "docs/phase14-day1-vps-deployment-plan.md",
    "docs/phase14-day1-demo-operations-guide.md",
]

REQUIRED_ROUTES = {
    "/demo-environment/status",
    "/demo-environment/readiness",
    "/demo-environment/checklist",
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
    return show("Phase 14 Day 1 service, routes, and docs exist", not missing, ", ".join(missing))


def verify_routes_and_payloads() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        route_paths = {route.path for route in app.routes if hasattr(route, "methods")}
        missing_routes = REQUIRED_ROUTES - route_paths
        status = client.get("/demo-environment/status")
        readiness = client.get("/demo-environment/readiness")
        checklist = client.get("/demo-environment/checklist")
        payloads = [status.json(), readiness.json(), checklist.json()]
        checklist_sections = {section["name"] for section in checklist.json().get("sections", [])}
        passed = (
            not missing_routes
            and status.status_code == 200
            and readiness.status_code == 200
            and checklist.status_code == 200
            and status.json()["phase"] == "PHASE_14"
            and status.json()["environment"] == "DEMO"
            and status.json()["status"] == "NOT_READY"
            and readiness.json()["ready_for_demo_execution"] is False
            and checklist_sections == {"MT5", "VPS", "MONITORING", "SAFETY"}
            and all(safety_ok(payload) for payload in payloads)
        )
        return show("Demo environment routes and safe payloads work", passed, ", ".join(sorted(missing_routes)))
    except Exception as exc:
        return show("Demo environment routes and safe payloads work", False, str(exc))


def verify_no_execution_enabled() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        endpoints = [
            "/demo-environment/status",
            "/demo-environment/readiness",
            "/demo-environment/checklist",
            "/nifty50/execution/status",
            "/strategy-execution-bridge/status",
        ]
        payloads = [client.get(endpoint).json() for endpoint in endpoints]
        token = "mt5." + "order_send"
        order_matches = []
        for path in (PROJECT_ROOT / "backend").rglob("*.py"):
            if token in path.read_text(encoding="utf-8", errors="ignore"):
                order_matches.append(path.relative_to(PROJECT_ROOT).as_posix())
        passed = (
            all(safety_ok(payload) for payload in payloads)
            and order_matches == ["backend/demo_execution/mt5_demo_executor.py"]
        )
        return show("No live or broker execution path enabled", passed, ", ".join(order_matches))
    except Exception as exc:
        return show("No live or broker execution path enabled", False, str(exc))


def main() -> int:
    print("Phase 14 Day 1 Demo Environment Verification")
    print("=" * 70)
    checks = [
        verify_files(),
        verify_routes_and_payloads(),
        verify_no_execution_enabled(),
    ]
    print("=" * 70)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
