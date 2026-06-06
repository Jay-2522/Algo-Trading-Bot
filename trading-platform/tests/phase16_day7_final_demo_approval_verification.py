import sys
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

REQUIRED_FILES = [
    "backend/mt5_demo/demo_final_approval_service.py",
    "docs/phase16-final-demo-order-approval-summary.md",
]

ROUTES = {
    "/mt5-demo/final-demo-approval/status",
    "/mt5-demo/final-demo-approval/run-review",
    "/mt5-demo/final-demo-approval/latest",
    "/mt5-demo/final-demo-approval/history",
    "/mt5-demo/final-demo-approval/revoke",
}

DECISIONS = {
    "APPROVED_FOR_FUTURE_SINGLE_DEMO_ORDER_TEST",
    "NOT_APPROVED",
    "BLOCKED_BY_SAFETY",
    "BLOCKED_BY_MISSING_READINESS",
    "BLOCKED_BY_MISSING_MANUAL_CONFIRMATION",
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
    return show("Final approval service and docs exist", not missing, ", ".join(missing))


def verify_routes_and_approval() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        paths = {route.path for route in app.routes if hasattr(route, "methods")}
        missing = sorted(ROUTES - paths)
        status = client.get("/mt5-demo/final-demo-approval/status")
        review = client.post("/mt5-demo/final-demo-approval/run-review")
        latest = client.get("/mt5-demo/final-demo-approval/latest")
        history = client.get("/mt5-demo/final-demo-approval/history")
        revoke = client.post("/mt5-demo/final-demo-approval/revoke")
        review_json = review.json()
        approved_count_ok = review_json.get("approved_trade_count") == (1 if review_json.get("approved_for_future_demo_order") else 0)
        payloads = [status.json(), review_json, latest.json(), history.json(), revoke.json()]
        passed = (
            not missing
            and all(response.status_code == 200 for response in [status, review, latest, history, revoke])
            and review_json.get("decision") in DECISIONS
            and approved_count_ok
            and review_json.get("max_demo_lot") == 0.01
            and review_json.get("manual_confirmation_required") is True
            and review_json.get("execution_allowed") is False
            and review_json.get("live_execution_enabled") is False
            and review_json.get("broker_execution_enabled") is False
            and latest.json().get("approval_id") == review_json.get("approval_id")
            and isinstance(history.json(), list)
            and len(history.json()) >= 1
            and revoke.json().get("decision") == "NOT_APPROVED"
            and revoke.json().get("approved_for_future_demo_order") is False
            and all(safety_ok(payload) for payload in payloads)
        )
        return show("Final approval routes review and revoke safely", passed, ", ".join(missing))
    except Exception as exc:
        return show("Final approval routes review and revoke safely", False, str(exc))


def verify_no_order_send_added() -> bool:
    token = "mt5." + "order_send"
    matches = [
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in (PROJECT_ROOT / "backend").rglob("*.py")
        if token in path.read_text(encoding="utf-8", errors="ignore")
    ]
    return show("No new mt5 order execution path was added", matches == ["backend/demo_execution/mt5_demo_executor.py"], ", ".join(matches))


def main() -> int:
    print("Phase 16 Day 7 Final Demo Approval Verification")
    print("=" * 78)
    checks = [verify_files(), verify_routes_and_approval(), verify_no_order_send_added()]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
