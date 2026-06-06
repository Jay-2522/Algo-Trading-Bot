import sys
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


DAY6_ROUTES = {
    "/demo-validation/e2e/status",
    "/demo-validation/e2e/run",
    "/demo-validation/e2e/latest",
    "/demo-validation/e2e/history",
}

DAY7_ROUTES = {
    "/demo-validation/soak/status",
    "/demo-validation/soak/readiness",
    "/demo-validation/soak/checklist",
    "/demo-validation/soak/preflight",
}

SYMBOL_ROUTES = {
    "/demo-validation/xauusd/status",
    "/demo-validation/xauusd/run",
    "/demo-validation/eurusd/status",
    "/demo-validation/eurusd/run",
    "/demo-validation/nifty50/status",
    "/demo-validation/nifty50/run",
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


def no_fake_trade_or_pnl(payload: Any) -> bool:
    for key, value in walk(payload):
        key_text = str(key).lower()
        value_text = str(value).lower()
        if key in {"fake_trades_created", "fake_pnl_created", "trade_journal_records_created"} and value is not False:
            return False
        if key_text in {"pnl", "profit", "profit_loss", "realized_pnl"} and value not in {0, 0.0, None, False}:
            return False
        if "fake +$" in value_text or "100% win" in value_text:
            return False
    return True


def verify_combined_routes_and_runs() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        route_paths = {route.path for route in app.routes if hasattr(route, "methods")}
        missing = sorted((DAY6_ROUTES | DAY7_ROUTES | SYMBOL_ROUTES) - route_paths)
        e2e = client.post("/demo-validation/e2e/run")
        soak = client.post("/demo-validation/soak/preflight")
        xauusd = client.post("/demo-validation/xauusd/run")
        eurusd = client.post("/demo-validation/eurusd/run")
        nifty50 = client.post("/demo-validation/nifty50/run")
        payloads = [e2e.json(), soak.json(), xauusd.json(), eurusd.json(), nifty50.json()]
        passed = (
            not missing
            and all(response.status_code == 200 for response in [e2e, soak, xauusd, eurusd, nifty50])
            and e2e.json()["symbols_tested"] == ["XAUUSD", "EURUSD", "NIFTY50"]
            and soak.json()["phase"] == "PHASE_14_DAY_7"
            and soak.json()["all_safety_locked"] is True
            and xauusd.json()["symbol"] == "XAUUSD"
            and eurusd.json()["symbol"] == "EURUSD"
            and nifty50.json()["symbol"] == "NIFTY50"
            and all(safety_ok(payload) for payload in payloads)
            and all(no_fake_trade_or_pnl(payload) for payload in payloads)
        )
        return show("Day 6, Day 7, and symbol validation routes run safely", passed, ", ".join(missing))
    except Exception as exc:
        return show("Day 6, Day 7, and symbol validation routes run safely", False, str(exc))


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


def main() -> int:
    print("Phase 14 Day 6 + Day 7 Combined Verification")
    print("=" * 78)
    checks = [
        verify_combined_routes_and_runs(),
        verify_no_order_send_added(),
        verify_no_external_broker_calls(),
    ]
    print("=" * 78)
    if all(checks):
        print("PHASE 14 DAY 6 + DAY 7 COMBINED RESULT: PASS")
        return 0
    print("PHASE 14 DAY 6 + DAY 7 COMBINED RESULT: FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
