import sys
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


REQUIRED_FILES = [
    "backend/demo_validation/e2e_demo_validation_service.py",
    "backend/api/demo_validation_routes.py",
    "docs/phase14-day6-e2e-demo-preview-validation.md",
]

E2E_ROUTES = {
    "/demo-validation/e2e/status",
    "/demo-validation/e2e/run",
    "/demo-validation/e2e/latest",
    "/demo-validation/e2e/history",
}

PREVIOUS_ROUTES = {
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
    return show("E2E demo preview service, routes, and docs exist", not missing, ", ".join(missing))


def verify_routes_and_e2e_run() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        route_paths = {route.path for route in app.routes if hasattr(route, "methods")}
        missing = sorted((E2E_ROUTES | PREVIOUS_ROUTES) - route_paths)
        status = client.get("/demo-validation/e2e/status")
        run = client.post("/demo-validation/e2e/run")
        latest = client.get("/demo-validation/e2e/latest")
        history = client.get("/demo-validation/e2e/history")
        payload = run.json()
        passed = (
            not missing
            and status.status_code == 200
            and run.status_code == 200
            and latest.status_code == 200
            and history.status_code == 200
            and payload["environment"] == "DEMO_PREVIEW"
            and payload["symbols_tested"] == ["XAUUSD", "EURUSD", "NIFTY50"]
            and payload["all_safety_locked"] is True
            and payload["execution_allowed"] is False
            and payload["preview_only"] is True
            and payload["live_execution_enabled"] is False
            and payload["broker_execution_enabled"] is False
            and payload["status"] in {"PASS", "WARNING"}
            and payload["symbol_results"]["XAUUSD"]["symbol"] == "XAUUSD"
            and payload["symbol_results"]["EURUSD"]["symbol"] == "EURUSD"
            and payload["symbol_results"]["NIFTY50"]["symbol"] == "NIFTY50"
            and all(payload["pipeline_checks"].values())
            and latest.json()["validation_id"] == payload["validation_id"]
            and isinstance(history.json(), list)
            and len(history.json()) >= 1
            and all(safety_ok(item) for item in [status.json(), payload, latest.json(), history.json()])
        )
        return show("E2E demo preview routes run safely", passed, ", ".join(missing))
    except Exception as exc:
        return show("E2E demo preview routes run safely", False, str(exc))


def verify_no_fake_trade_or_pnl() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        payload = client.post("/demo-validation/e2e/run").json()
        disallowed_values: list[str] = []
        for key, value in walk(payload):
            key_text = str(key).lower()
            value_text = str(value).lower()
            if key in {"fake_trades_created", "fake_pnl_created", "trade_journal_records_created"} and value is not False:
                disallowed_values.append(f"{key}={value}")
            if key_text in {"pnl", "profit", "profit_loss", "realized_pnl"} and value not in {0, 0.0, None, False}:
                disallowed_values.append(f"{key}={value}")
            if "fake +$" in value_text or "100% win" in value_text:
                disallowed_values.append(f"{key}={value}")
        return show("No fake trades or fake P&L created", not disallowed_values, ", ".join(disallowed_values))
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
        PROJECT_ROOT / "backend" / "demo_validation" / "e2e_demo_validation_service.py",
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
    print("Phase 14 Day 6 E2E Demo Preview Verification")
    print("=" * 78)
    checks = [
        verify_files(),
        verify_routes_and_e2e_run(),
        verify_no_fake_trade_or_pnl(),
        verify_no_external_broker_calls(),
        verify_no_order_send_added(),
    ]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
