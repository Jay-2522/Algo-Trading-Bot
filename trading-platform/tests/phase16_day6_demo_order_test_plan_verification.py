import sys
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

REQUIRED_FILES = [
    "backend/mt5_demo/demo_trade_test_plan_service.py",
    "docs/phase16-day6-demo-order-test-plan.md",
]

ROUTES = {
    "/mt5-demo/test-plan/status",
    "/mt5-demo/test-plan/generate",
    "/mt5-demo/test-plan/latest",
    "/mt5-demo/test-plan/history",
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


def verify_files() -> bool:
    missing = [path for path in REQUIRED_FILES if not (PROJECT_ROOT / path).is_file()]
    return show("Test-plan service and docs exist", not missing, ", ".join(missing))


def verify_routes_and_plan() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        paths = {route.path for route in app.routes if hasattr(route, "methods")}
        missing = sorted(ROUTES - paths)
        status = client.get("/mt5-demo/test-plan/status")
        plan = client.post("/mt5-demo/test-plan/generate")
        latest = client.get("/mt5-demo/test-plan/latest")
        history = client.get("/mt5-demo/test-plan/history")
        plan_json = plan.json()
        failure_scenarios = plan_json.get("failure_scenarios", [])
        rollback_steps = plan_json.get("rollback_steps", [])
        payloads = [status.json(), plan_json, latest.json(), history.json()]
        passed = (
            not missing
            and all(response.status_code == 200 for response in [status, plan, latest, history])
            and plan_json.get("status") == "READY_FOR_FUTURE_DEMO_TESTING"
            and len(plan_json.get("prerequisites", [])) >= 19
            and len(failure_scenarios) >= 7
            and all(item.get("response") == "stop trade" for item in failure_scenarios)
            and all(item.get("execution_instruction") == "do not execute" for item in failure_scenarios)
            and all(item.get("operator_action") == "notify operator" for item in failure_scenarios)
            and [item.get("action") for item in rollback_steps] == [
                "Disable authorization",
                "Disable demo testing",
                "Clear pending request",
                "Reset execution gate",
                "Return system to simulation mode",
            ]
            and plan_json.get("recommended_symbol") == "EURUSD"
            and plan_json.get("recommended_lot") == 0.01
            and plan_json.get("recommended_trade_count") == 1
            and plan_json.get("execution_allowed") is False
            and plan_json.get("live_execution_enabled") is False
            and plan_json.get("broker_execution_enabled") is False
            and latest.json().get("plan_id") == plan_json.get("plan_id")
            and isinstance(history.json(), list)
            and len(history.json()) >= 1
            and all(safety_ok(payload) for payload in payloads)
        )
        return show("Test-plan routes generate controlled checklist safely", passed, ", ".join(missing))
    except Exception as exc:
        return show("Test-plan routes generate controlled checklist safely", False, str(exc))


def verify_no_order_send_added() -> bool:
    token = "mt5." + "order_send"
    matches = [
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in (PROJECT_ROOT / "backend").rglob("*.py")
        if token in path.read_text(encoding="utf-8", errors="ignore")
    ]
    return show("No new mt5 order execution path was added", matches == ["backend/demo_execution/mt5_demo_executor.py"], ", ".join(matches))


def main() -> int:
    print("Phase 16 Day 6 Demo Order Test Plan Verification")
    print("=" * 78)
    checks = [verify_files(), verify_routes_and_plan(), verify_no_order_send_added()]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
