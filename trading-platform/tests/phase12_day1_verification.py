import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def verify_files() -> bool:
    files = [
        "backend/nifty50/__init__.py",
        "backend/nifty50/nifty_models.py",
        "backend/nifty50/broker_adapter_base.py",
        "backend/nifty50/indian_broker_registry.py",
        "backend/nifty50/nse_market_session.py",
        "backend/nifty50/nifty_market_data_service.py",
        "backend/nifty50/nifty_readiness_service.py",
        "backend/api/nifty50_routes.py",
        "docs/phase-12-day-1-progress.md",
        "docs/nifty50-broker-architecture.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    return show("NIFTY50 package, services, routes, and docs exist", not missing, ", ".join(missing))


def verify_routes_and_payloads() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        route_paths = {route.path for route in app.routes if hasattr(route, "methods") and "GET" in route.methods}
        required = {
            "/nifty50/status",
            "/nifty50/instrument",
            "/nifty50/brokers",
            "/nifty50/brokers/recommended",
            "/nifty50/session",
            "/nifty50/market-data/snapshot",
            "/nifty50/readiness",
            "/nifty50/blockers",
        }
        instrument = client.get("/nifty50/instrument")
        brokers = client.get("/nifty50/brokers")
        recommended = client.get("/nifty50/brokers/recommended")
        session = client.get("/nifty50/session")
        snapshot = client.get("/nifty50/market-data/snapshot")
        readiness = client.get("/nifty50/readiness")
        blockers = client.get("/nifty50/blockers")
        instrument_payload = instrument.json()
        broker_payload = brokers.json()
        recommended_payload = recommended.json()
        snapshot_payload = snapshot.json()
        readiness_payload = readiness.json()
        blockers_payload = blockers.json()
        no_fake_price = all(snapshot_payload[field] is None for field in ["last_price", "open", "high", "low", "previous_close", "volume"])
        passed = (
            required <= route_paths
            and instrument.status_code == 200
            and brokers.status_code == 200
            and recommended.status_code == 200
            and session.status_code == 200
            and snapshot.status_code == 200
            and readiness.status_code == 200
            and blockers.status_code == 200
            and instrument_payload["symbol"] == "NIFTY50"
            and instrument_payload["exchange"] == "NSE"
            and instrument_payload["instrument_type"] == "INDEX"
            and instrument_payload["currency"] == "INR"
            and {broker["broker_id"] for broker in broker_payload} >= {"dhan", "angel_one", "fyers", "upstox", "zerodha"}
            and recommended_payload["selected_broker"] is None
            and "Dhan" in str(recommended_payload)
            and "Angel One" in str(recommended_payload)
            and snapshot_payload["placeholder"] is True
            and snapshot_payload["data_source"] == "PLACEHOLDER"
            and no_fake_price
            and readiness_payload["blockers"]
            and readiness_payload["simulation_only"] is True
            and readiness_payload["live_execution_enabled"] is False
            and readiness_payload["broker_execution_enabled"] is False
            and "Indian broker not selected" in blockers_payload["blockers"]
        )
        return show("NIFTY50 routes, instrument, brokers, session, placeholder snapshot, and blockers work", passed)
    except Exception as exc:
        return show("NIFTY50 routes, instrument, brokers, session, placeholder snapshot, and blockers work", False, str(exc))


def verify_no_broker_api_calls() -> bool:
    try:
        forbidden = ["requests.", "httpx.", "aiohttp", "urllib.request", "yfinance", "kiteconnect", "smartapi", "dhanhq", "fyers_apiv3", "upstox_client"]
        offenders = []
        for path in (PROJECT_ROOT / "backend" / "nifty50").rglob("*.py"):
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            for token in forbidden:
                if token.lower() in text:
                    offenders.append(f"{path.name}:{token}")
        return show("No broker API or external market data calls added", not offenders, ", ".join(offenders))
    except Exception as exc:
        return show("No broker API or external market data calls added", False, str(exc))


def verify_executive_update() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        instruments = client.get("/client-analytics/executive/instruments").json()
        summary = client.get("/client-analytics/executive/summary").json()
        completion = client.get("/client-analytics/executive/completion").json()
        nifty = next((item for item in instruments["instruments"] if item["symbol"] == "NIFTY50"), {})
        passed = (
            nifty["status"] in {"FOUNDATION_READY", "STRATEGY_FOUNDATION_READY"}
            and nifty["ready"] is False
            and "broker" in nifty["reason"].lower()
            and summary["nifty50_ready"] is False
            and 90 <= summary["overall_completion_percentage"] < 100
            and completion["overall_completion_percentage"] < 100
        )
        return show("Executive dashboard updates NIFTY50 foundation status without marking it ready", passed)
    except Exception as exc:
        return show("Executive dashboard updates NIFTY50 foundation status without marking it ready", False, str(exc))


def verify_phase11_preserved() -> bool:
    try:
        from backend.main import app

        required = {
            "/client-analytics/executive/status",
            "/client-analytics/executive/summary",
            "/client-analytics/strategy/status",
            "/client-analytics/reports/status",
            "/client-analytics/accounts",
        }
        registered = {route.path for route in app.routes if hasattr(route, "methods") and "GET" in route.methods}
        return show("Phase 11 routes are preserved", required <= registered)
    except Exception as exc:
        return show("Phase 11 routes are preserved", False, str(exc))


def verify_no_order_send() -> bool:
    try:
        token = "mt5." + "order_send"
        matches = []
        for path in (PROJECT_ROOT / "backend").rglob("*.py"):
            if path.is_file() and token in path.read_text(encoding="utf-8", errors="ignore"):
                matches.append(path.relative_to(PROJECT_ROOT).as_posix())
        return show("No new mt5.order_send added", matches == ["backend/demo_execution/mt5_demo_executor.py"], ", ".join(matches))
    except Exception as exc:
        return show("No new mt5.order_send added", False, str(exc))


def main() -> int:
    print("Phase 12 Day 1 NIFTY50 Broker Architecture & Market Data Foundation Verification")
    print("=" * 86)
    checks = [
        verify_files(),
        verify_routes_and_payloads(),
        verify_no_broker_api_calls(),
        verify_executive_update(),
        verify_phase11_preserved(),
        verify_no_order_send(),
    ]
    print("=" * 86)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
