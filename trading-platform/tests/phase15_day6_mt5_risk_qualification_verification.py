import sys
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

REQUIRED_FILES = [
    "backend/mt5_demo/mt5_risk_qualification_service.py",
    "docs/phase15-day6-mt5-risk-qualification.md",
]

ROUTES = {
    "/mt5-demo/risk-qualification/status",
    "/mt5-demo/risk-qualification/{symbol}/evaluate",
    "/mt5-demo/risk-qualification/evaluate-all",
    "/mt5-demo/risk-qualification/{symbol}/latest",
    "/mt5-demo/risk-qualification/history",
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
        if key in {"live_execution_enabled", "broker_execution_enabled", "execution_allowed", "execution_triggered", "forced_signal"} and value is True:
            return False
    return True


def verify_files() -> bool:
    missing = [path for path in REQUIRED_FILES if not (PROJECT_ROOT / path).is_file()]
    return show("Risk qualification service and docs exist", not missing, ", ".join(missing))


def verify_routes_and_risk() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        paths = {route.path for route in app.routes if hasattr(route, "methods")}
        missing = sorted(ROUTES - paths)
        status = client.get("/mt5-demo/risk-qualification/status")
        eurusd = client.post("/mt5-demo/risk-qualification/EURUSD/evaluate")
        xauusd = client.post("/mt5-demo/risk-qualification/XAUUSD/evaluate")
        all_result = client.post("/mt5-demo/risk-qualification/evaluate-all")
        eur_latest = client.get("/mt5-demo/risk-qualification/EURUSD/latest")
        xau_latest = client.get("/mt5-demo/risk-qualification/XAUUSD/latest")
        history = client.get("/mt5-demo/risk-qualification/history")
        payloads = [status.json(), eurusd.json(), xauusd.json(), all_result.json(), eur_latest.json(), xau_latest.json(), history.json()]
        statuses = {"APPROVED", "BLOCKED", "WAIT", "NO_SIGNAL", "NOT_RUN"}
        passed = (
            not missing
            and all(response.status_code == 200 for response in [status, eurusd, xauusd, all_result, eur_latest, xau_latest, history])
            and eurusd.json()["qualification_status"] in statuses
            and xauusd.json()["qualification_status"] in statuses
            and eurusd.json()["risk_checked"] is True
            and xauusd.json()["risk_checked"] is True
            and all_result.json()["all_safety_locked"] is True
            and isinstance(history.json(), list)
            and all(safety_ok(payload) for payload in payloads)
        )
        return show("Risk qualification routes evaluate safely", passed, ", ".join(missing))
    except Exception as exc:
        return show("Risk qualification routes evaluate safely", False, str(exc))


def verify_no_order_send_added() -> bool:
    token = "mt5." + "order_send"
    matches = [
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in (PROJECT_ROOT / "backend").rglob("*.py")
        if token in path.read_text(encoding="utf-8", errors="ignore")
    ]
    return show("No new mt5 order execution path was added", matches == ["backend/demo_execution/mt5_demo_executor.py"], ", ".join(matches))


def main() -> int:
    print("Phase 15 Day 6 MT5 Risk Qualification Verification")
    print("=" * 78)
    checks = [verify_files(), verify_routes_and_risk(), verify_no_order_send_added()]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
