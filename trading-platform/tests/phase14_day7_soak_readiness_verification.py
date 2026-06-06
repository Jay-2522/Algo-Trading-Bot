import sys
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


REQUIRED_FILES = [
    "backend/demo_validation/soak_test_readiness_service.py",
    "backend/api/demo_validation_routes.py",
    "docs/phase14-day7-soak-testing-preparation.md",
    "docs/phase14-final-demo-validation-summary.md",
]

SOAK_ROUTES = {
    "/demo-validation/soak/status",
    "/demo-validation/soak/readiness",
    "/demo-validation/soak/checklist",
    "/demo-validation/soak/preflight",
}

DAY6_ROUTES = {
    "/demo-validation/e2e/status",
    "/demo-validation/e2e/run",
    "/demo-validation/e2e/latest",
    "/demo-validation/e2e/history",
}

SYMBOL_ROUTES = {
    "/demo-validation/xauusd/status",
    "/demo-validation/eurusd/status",
    "/demo-validation/nifty50/status",
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
    return show("Soak readiness service, routes, and docs exist", not missing, ", ".join(missing))


def verify_routes_and_preflight() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        route_paths = {route.path for route in app.routes if hasattr(route, "methods")}
        missing = sorted((SOAK_ROUTES | DAY6_ROUTES | SYMBOL_ROUTES) - route_paths)
        status = client.get("/demo-validation/soak/status")
        readiness = client.get("/demo-validation/soak/readiness")
        checklist = client.get("/demo-validation/soak/checklist")
        preflight = client.post("/demo-validation/soak/preflight")
        preflight_payload = preflight.json()
        checklist_payload = checklist.json()
        passed = (
            not missing
            and status.status_code == 200
            and readiness.status_code == 200
            and checklist.status_code == 200
            and preflight.status_code == 200
            and preflight_payload["phase"] == "PHASE_14_DAY_7"
            and preflight_payload["environment"] == "DEMO_SOAK_PREPARATION"
            and preflight_payload["backend_ready"] is True
            and preflight_payload["demo_environment_ready"] is True
            and preflight_payload["mt5_demo_ready"] is True
            and preflight_payload["xauusd_validation_ready"] is True
            and preflight_payload["eurusd_validation_ready"] is True
            and preflight_payload["nifty50_validation_ready"] is True
            and preflight_payload["e2e_preview_ready"] is True
            and preflight_payload["all_safety_locked"] is True
            and preflight_payload["execution_allowed"] is False
            and preflight_payload["preview_only"] is True
            and preflight_payload["live_execution_enabled"] is False
            and preflight_payload["broker_execution_enabled"] is False
            and preflight_payload["status"] in {"READY_FOR_SOAK_TEST", "NOT_READY"}
            and {section["name"] for section in checklist_payload["sections"]} == {"Backend", "Demo", "Safety", "Monitoring"}
            and all(safety_ok(item) for item in [status.json(), readiness.json(), checklist_payload, preflight_payload])
        )
        return show("Soak readiness routes and preflight run safely", passed, ", ".join(missing))
    except Exception as exc:
        return show("Soak readiness routes and preflight run safely", False, str(exc))


def verify_no_fake_trade_or_pnl() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        payload = client.post("/demo-validation/soak/preflight").json()
        matches: list[str] = []
        for key, value in walk(payload):
            key_text = str(key).lower()
            value_text = str(value).lower()
            if key in {"fake_trades_created", "fake_pnl_created", "trade_journal_records_created"} and value is not False:
                matches.append(f"{key}={value}")
            if key_text in {"pnl", "profit", "profit_loss", "realized_pnl"} and value not in {0, 0.0, None, False}:
                matches.append(f"{key}={value}")
            if "fake +$" in value_text or "100% win" in value_text:
                matches.append(f"{key}={value}")
        return show("No fake trades or fake P&L created", not matches, ", ".join(matches))
    except Exception as exc:
        return show("No fake trades or fake P&L created", False, str(exc))


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
        PROJECT_ROOT / "backend" / "demo_validation" / "soak_test_readiness_service.py",
        PROJECT_ROOT / "backend" / "api" / "demo_validation_routes.py",
    ]
    matches: list[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for token in forbidden_tokens:
            if token in text:
                matches.append(f"{path.relative_to(PROJECT_ROOT).as_posix()}::{token}")
    return show("No external broker/API calls added", not matches, ", ".join(matches))


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
    print("Phase 14 Day 7 Soak Readiness Verification")
    print("=" * 78)
    checks = [
        verify_files(),
        verify_routes_and_preflight(),
        verify_no_fake_trade_or_pnl(),
        verify_no_external_broker_calls(),
        verify_no_order_send_added(),
    ]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
