import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


REQUIRED_FILES = [
    "backend/mt5_demo/market_snapshot_service.py",
    "backend/mt5_demo/mt5_market_data_service.py",
    "backend/api/mt5_demo_routes.py",
    "docs/phase15-day3-market-pipeline.md",
]

REQUIRED_ROUTES = {"/mt5-demo/overview"}


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
    return show("Market snapshot service and docs exist", not missing, ", ".join(missing))


def verify_overview_route() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        route_paths = {route.path for route in app.routes if hasattr(route, "methods")}
        missing = sorted(REQUIRED_ROUTES - route_paths)
        response = client.get("/mt5-demo/overview")
        payload = response.json()
        symbols = payload.get("symbols", {})
        eurusd = symbols.get("EURUSD", {})
        xauusd = symbols.get("XAUUSD", {})
        passed = (
            not missing
            and response.status_code == 200
            and payload.get("status") in {"READY", "STALE", "OFFLINE"}
            and payload.get("source") == "MT5_DEMO"
            and "EURUSD" in symbols
            and "XAUUSD" in symbols
            and eurusd.get("tick_status") in {"OK", "STALE_OR_UNAVAILABLE", "MT5_UNAVAILABLE", "SYMBOL_UNAVAILABLE", "TICK_UNAVAILABLE", "TICK_READ_FAILED"}
            and xauusd.get("tick_status") in {"OK", "STALE_OR_UNAVAILABLE", "MT5_UNAVAILABLE", "SYMBOL_UNAVAILABLE", "TICK_UNAVAILABLE", "TICK_READ_FAILED"}
            and eurusd.get("freshness") in {"READY", "STALE", "OFFLINE"}
            and xauusd.get("freshness") in {"READY", "STALE", "OFFLINE"}
            and isinstance(eurusd.get("latest_candle_timestamps"), dict)
            and isinstance(xauusd.get("latest_candle_timestamps"), dict)
            and safety_ok(payload)
        )
        return show("MT5 demo overview route works safely", passed, ", ".join(missing))
    except Exception as exc:
        return show("MT5 demo overview route works safely", False, str(exc))


def verify_freshness_calculation() -> bool:
    try:
        from backend.mt5_demo.market_snapshot_service import MarketSnapshotService

        service = MarketSnapshotService()
        now = datetime.now(timezone.utc)
        checks = [
            service.calculate_freshness((now - timedelta(minutes=1)).isoformat()) == "READY",
            service.calculate_freshness((now - timedelta(minutes=10)).isoformat()) == "STALE",
            service.calculate_freshness((now - timedelta(minutes=31)).isoformat()) == "OFFLINE",
            service.calculate_freshness(None) == "OFFLINE",
        ]
        return show("Freshness calculation supports READY, STALE, and OFFLINE", all(checks))
    except Exception as exc:
        return show("Freshness calculation supports READY, STALE, and OFFLINE", False, str(exc))


def verify_dashboard_integration() -> bool:
    files = [
        PROJECT_ROOT / "frontend" / "lib" / "dashboard-api.ts",
        PROJECT_ROOT / "frontend" / "components" / "dashboard" / "DashboardShell.tsx",
        PROJECT_ROOT / "frontend" / "hooks" / "useDashboardData.ts",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in files)
    required = [
        "/mt5-demo/overview",
        "EURUSD Demo Bid",
        "XAUUSD Demo Bid",
        "Market Freshness",
        "mt5MarketOverview",
    ]
    missing = [token for token in required if token not in combined]
    forbidden = ["fake +$900", "fake +$100", "100% win rate"]
    forbidden_hits = [token for token in forbidden if token.lower() in combined.lower()]
    return show("Dashboard uses MT5 demo overview without fake market metrics", not missing and not forbidden_hits, ", ".join(missing + forbidden_hits))


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
    print("Phase 15 Day 3 MT5 Market Pipeline Verification")
    print("=" * 78)
    checks = [
        verify_files(),
        verify_overview_route(),
        verify_freshness_calculation(),
        verify_dashboard_integration(),
        verify_no_order_send_added(),
    ]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
