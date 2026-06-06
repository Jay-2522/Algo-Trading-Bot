import sys
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

REQUIRED_FILES = [
    "backend/mt5_demo/demo_execution_readiness_service.py",
    "docs/phase16-day5-execution-readiness-review.md",
]

ROUTES = {
    "/mt5-demo/readiness/status",
    "/mt5-demo/readiness/run-audit",
    "/mt5-demo/readiness/latest",
    "/mt5-demo/readiness/history",
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
    return show("Readiness service and docs exist", not missing, ", ".join(missing))


def verify_routes_and_audit() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        paths = {route.path for route in app.routes if hasattr(route, "methods")}
        missing = sorted(ROUTES - paths)
        status = client.get("/mt5-demo/readiness/status")
        audit = client.post("/mt5-demo/readiness/run-audit")
        latest = client.get("/mt5-demo/readiness/latest")
        history = client.get("/mt5-demo/readiness/history")
        audit_json = audit.json()
        payloads = [status.json(), audit_json, latest.json(), history.json()]
        expected_components = {
            "mt5_connection",
            "market_data",
            "historical_data",
            "strategy_feed",
            "strategy_consumption",
            "risk_qualification",
            "execution_gate",
            "authorization_layer",
            "preflight_validation",
            "execution_simulator",
        }
        passed = (
            not missing
            and all(response.status_code == 200 for response in [status, audit, latest, history])
            and isinstance(audit_json.get("overall_score"), int)
            and 0 <= audit_json["overall_score"] <= 100
            and audit_json.get("overall_status") in {"READY", "PARTIALLY_READY", "NOT_READY"}
            and set(audit_json.get("component_scores", {})) == expected_components
            and isinstance(audit_json.get("blockers"), list)
            and len(audit_json["blockers"]) >= 1
            and audit_json["execution_allowed"] is False
            and audit_json["live_execution_enabled"] is False
            and audit_json["broker_execution_enabled"] is False
            and latest.json().get("audit_id") == audit_json.get("audit_id")
            and isinstance(history.json(), list)
            and len(history.json()) >= 1
            and all(safety_ok(payload) for payload in payloads)
        )
        return show("Readiness routes run audit safely", passed, ", ".join(missing))
    except Exception as exc:
        return show("Readiness routes run audit safely", False, str(exc))


def verify_no_order_send_added() -> bool:
    token = "mt5." + "order_send"
    matches = [
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in (PROJECT_ROOT / "backend").rglob("*.py")
        if token in path.read_text(encoding="utf-8", errors="ignore")
    ]
    return show("No new mt5 order execution path was added", matches == ["backend/demo_execution/mt5_demo_executor.py"], ", ".join(matches))


def main() -> int:
    print("Phase 16 Day 5 Execution Readiness Review Verification")
    print("=" * 78)
    checks = [verify_files(), verify_routes_and_audit(), verify_no_order_send_added()]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
