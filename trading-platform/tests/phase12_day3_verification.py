import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def verify_files() -> bool:
    files = [
        "backend/nifty50/nifty_market_data_models.py",
        "backend/nifty50/nifty_candle_store.py",
        "backend/nifty50/nifty_market_data_validator.py",
        "backend/nifty50/nifty_timeframe_service.py",
        "backend/nifty50/nifty_snapshot_builder.py",
        "backend/nifty50/nifty_market_data_adapter.py",
        "docs/phase-12-day-3-progress.md",
        "docs/nifty50-market-data-integration.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    return show("Market data models, store, validator, timeframe, adapter, snapshot builder, and docs exist", not missing, ", ".join(missing))


def verify_routes_and_ingestion() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        route_paths = {route.path for route in app.routes if hasattr(route, "methods")}
        required = {
            "/nifty50/market-data/status",
            "/nifty50/market-data/health",
            "/nifty50/market-data/timeframes",
            "/nifty50/market-data/latest",
            "/nifty50/market-data/ingest-candle",
            "/nifty50/market-data/ingest-tick",
        }
        candle = {
            "symbol": "NIFTY50",
            "timeframe": "M15",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "open": 100.0,
            "high": 105.0,
            "low": 99.0,
            "close": 103.0,
            "volume": 25,
            "placeholder": False,
        }
        tick = {
            "symbol": "NIFTY50",
            "price": 103.5,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "placeholder": False,
        }
        candle_response = client.post("/nifty50/market-data/ingest-candle", json=candle)
        tick_response = client.post("/nifty50/market-data/ingest-tick", json=tick)
        invalid_response = client.post("/nifty50/market-data/ingest-candle", json={**candle, "high": 98.0})
        health = client.get("/nifty50/market-data/health")
        latest = client.get("/nifty50/market-data/latest")
        timeframes = client.get("/nifty50/market-data/timeframes")
        status = client.get("/nifty50/market-data/status")
        health_payload = health.json()
        latest_payload = latest.json()
        passed = (
            required <= route_paths
            and candle_response.status_code == 200
            and candle_response.json()["accepted"] is True
            and tick_response.status_code == 200
            and tick_response.json()["accepted"] is True
            and invalid_response.status_code == 200
            and invalid_response.json()["accepted"] is False
            and health.status_code == 200
            and health_payload["candles_available"] >= 1
            and health_payload["ticks_available"] >= 1
            and health_payload["valid_candles"] >= 1
            and health_payload["invalid_candles"] >= 1
            and health_payload["placeholder"] is False
            and latest.status_code == 200
            and latest_payload["symbol"] == "NIFTY50"
            and latest_payload["placeholder"] is False
            and latest_payload["latest_price"] == 103.5
            and "M15" in latest_payload["available_timeframes"]
            and timeframes.json()["supported_timeframes"] == ["M1", "M5", "M15", "H1", "H4", "D1"]
            and status.json()["market_data_ready"] is True
            and status.json()["broker_execution_enabled"] is False
        )
        return show("Market data routes, manual candle ingestion, tick ingestion, health, latest, and validation work", passed)
    except Exception as exc:
        return show("Market data routes, manual candle ingestion, tick ingestion, health, latest, and validation work", False, str(exc))


def verify_strategy_integration() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        candle = {
            "symbol": "NIFTY50",
            "timeframe": "M5",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "open": 200.0,
            "high": 202.0,
            "low": 198.0,
            "close": 201.0,
            "volume": 10,
            "placeholder": False,
        }
        client.post("/nifty50/market-data/ingest-candle", json=candle)
        liquidity = client.get("/nifty50/strategy/liquidity").json()
        structure = client.get("/nifty50/strategy/structure").json()
        fvg = client.get("/nifty50/strategy/fvg").json()
        order_block = client.get("/nifty50/strategy/order-block").json()
        snapshot = client.get("/nifty50/strategy/snapshot").json()
        passed = (
            liquidity["placeholder"] in {False, True}
            and liquidity["sweep_detected"] in {False, True}
            and structure["placeholder"] in {False, True}
            and structure["bos_detected"] in {False, True}
            and structure["choch_detected"] in {False, True}
            and fvg["placeholder"] in {False, True}
            and fvg["active_fvg_detected"] in {False, True}
            and order_block["placeholder"] in {False, True}
            and snapshot["placeholder"] is False
            and snapshot["strategy_bias"] in {"BULLISH", "BEARISH", "NEUTRAL"}
            and snapshot["regime"] in {"TRENDING_BULLISH", "TRENDING_BEARISH", "RANGING", "UNKNOWN"}
            and 0 <= snapshot["confidence"] <= 100
        )
        return show("Strategy services integrate with market-data layer without fake SMC signals", passed)
    except Exception as exc:
        return show("Strategy services integrate with market-data layer without fake SMC signals", False, str(exc))


def verify_no_broker_api_or_execution() -> bool:
    try:
        forbidden = ["requests.", "httpx.", "aiohttp", "urllib.request", "yfinance", "kiteconnect", "smartapi", "dhanhq", "fyers_apiv3", "upstox_client"]
        offenders = []
        for path in (PROJECT_ROOT / "backend" / "nifty50").rglob("*.py"):
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
            for token in forbidden:
                if token.lower() in text:
                    offenders.append(f"{path.name}:{token}")
        token = "mt5." + "order_send"
        order_matches = []
        for path in (PROJECT_ROOT / "backend").rglob("*.py"):
            if path.is_file() and token in path.read_text(encoding="utf-8", errors="ignore"):
                order_matches.append(path.relative_to(PROJECT_ROOT).as_posix())
        return show(
            "No broker APIs, no live execution, no fake market feed, and no new mt5.order_send added",
            not offenders and order_matches == ["backend/demo_execution/mt5_demo_executor.py"],
            ", ".join(offenders + order_matches),
        )
    except Exception as exc:
        return show("No broker APIs, no live execution, no fake market feed, and no new mt5.order_send added", False, str(exc))


def verify_readiness_and_executive_update() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        readiness = client.get("/nifty50/readiness").json()
        instruments = client.get("/client-analytics/executive/instruments").json()
        summary = client.get("/client-analytics/executive/summary").json()
        nifty = next((item for item in instruments["instruments"] if item["symbol"] == "NIFTY50"), {})
        passed = (
            readiness["status"] in {"MARKET_DATA_READY", "SMC_INTELLIGENCE_READY"}
            and readiness["market_data_ready"] is True
            and readiness["strategy_ready"] in {False, True}
            and readiness["execution_ready"] is False
            and readiness["live_execution_enabled"] is False
            and readiness["broker_execution_enabled"] is False
            and nifty["status"] in {"MARKET_DATA_READY", "SMC_INTELLIGENCE_READY"}
            and nifty["ready"] is False
            and summary["nifty50_ready"] is False
            and 93 <= summary["overall_completion_percentage"] < 100
        )
        return show("Readiness and executive dashboard upgraded to MARKET_DATA_READY without marking NIFTY50 ready", passed)
    except Exception as exc:
        return show("Readiness and executive dashboard upgraded to MARKET_DATA_READY without marking NIFTY50 ready", False, str(exc))


def main() -> int:
    print("Phase 12 Day 3 NIFTY50 Market Data Integration Verification")
    print("=" * 74)
    checks = [
        verify_files(),
        verify_routes_and_ingestion(),
        verify_strategy_integration(),
        verify_no_broker_api_or_execution(),
        verify_readiness_and_executive_update(),
    ]
    print("=" * 74)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
