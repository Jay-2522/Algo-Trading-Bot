import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


REQUIRED_FILES = [
    "backend/mt5_demo/mt5_market_data_service.py",
    "backend/api/mt5_demo_routes.py",
    "docs/phase15-day2-mt5-market-data-retrieval.md",
]

REQUIRED_ROUTES = {
    "/mt5-demo/market-data/status",
    "/mt5-demo/market-data/tick/{symbol}",
    "/mt5-demo/market-data/candles/{symbol}/{timeframe}",
    "/mt5-demo/market-data/spread/{symbol}",
}

TICK_PATHS = [
    "/mt5-demo/market-data/tick/EURUSD",
    "/mt5-demo/market-data/tick/XAUUSD",
]

CANDLE_PATHS = [
    "/mt5-demo/market-data/candles/EURUSD/M5",
    "/mt5-demo/market-data/candles/EURUSD/H1",
    "/mt5-demo/market-data/candles/XAUUSD/M5",
    "/mt5-demo/market-data/candles/XAUUSD/H1",
]

SPREAD_PATHS = [
    "/mt5-demo/market-data/spread/EURUSD",
    "/mt5-demo/market-data/spread/XAUUSD",
]


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


def valid_ok_tick(payload: dict[str, Any]) -> bool:
    try:
        bid = float(payload.get("bid") or 0)
        ask = float(payload.get("ask") or 0)
        timestamp = payload.get("timestamp")
        parsed = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        return bid > 0 and ask > 0 and parsed.timestamp() > 0
    except Exception:
        return False


def tick_payload_ok(payload: dict[str, Any]) -> bool:
    status = payload.get("status")
    if status == "OK":
        return valid_ok_tick(payload) and payload.get("freshness") == "READY" and payload.get("market_status") in {None, "MARKET_READY"}
    if status in {"STALE_OR_MARKET_CLOSED", "STALE_TICK"}:
        return (
            payload.get("freshness") in {"OFFLINE", "STALE"}
            and payload.get("message")
        )
    return status in {"MT5_UNAVAILABLE", "SYMBOL_UNAVAILABLE", "TICK_UNAVAILABLE", "TICK_READ_FAILED", "SYMBOL_TICK_UNAVAILABLE", "FEED_OFFLINE", "MARKET_CLOSED"}


def verify_files() -> bool:
    missing = [path for path in REQUIRED_FILES if not (PROJECT_ROOT / path).is_file()]
    return show("MT5 market-data service, routes, and docs exist", not missing, ", ".join(missing))


def verify_routes_and_payloads() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        route_paths = {route.path for route in app.routes if hasattr(route, "methods")}
        missing = sorted(REQUIRED_ROUTES - route_paths)
        responses = [client.get("/mt5-demo/market-data/status")]
        responses.extend(client.get(path) for path in TICK_PATHS)
        responses.extend(client.get(path) for path in CANDLE_PATHS)
        responses.extend(client.get(path) for path in SPREAD_PATHS)
        payloads = [response.json() for response in responses]
        ticks_ok = all(
            payload.get("symbol") in {"EURUSD", "XAUUSD"}
            and payload.get("source") in {"MT5_DEMO", "VANTAGE_DEMO"}
            and tick_payload_ok(payload)
            for payload in payloads[1:3]
        )
        candles_ok = all(
            payload.get("symbol") in {"EURUSD", "XAUUSD"}
            and payload.get("timeframe") in {"M5", "H1"}
            and payload.get("source") in {"MT5_DEMO", "VANTAGE_DEMO"}
            and isinstance(payload.get("candles"), list)
            and payload.get("status") in {"OK", "MT5_UNAVAILABLE", "SYMBOL_UNAVAILABLE", "CANDLES_UNAVAILABLE", "CANDLE_READ_FAILED"}
            for payload in payloads[3:7]
        )
        spreads_ok = all(
            payload.get("symbol") in {"EURUSD", "XAUUSD"}
            and payload.get("source") in {"MT5_DEMO", "VANTAGE_DEMO"}
            and tick_payload_ok(payload)
            for payload in payloads[7:]
        )
        passed = (
            not missing
            and all(response.status_code == 200 for response in responses)
            and payloads[0]["source"] == "MT5_DEMO"
            and "EURUSD" in payloads[0]["supported_symbols"]
            and "XAUUSD" in payloads[0]["supported_symbols"]
            and "M5" in payloads[0]["supported_timeframes"]
            and "H1" in payloads[0]["supported_timeframes"]
            and ticks_ok
            and candles_ok
            and spreads_ok
            and all(safety_ok(payload) for payload in payloads)
        )
        return show("MT5 market-data routes return safe payloads", passed, ", ".join(missing))
    except Exception as exc:
        return show("MT5 market-data routes return safe payloads", False, str(exc))


def verify_invalid_inputs() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        invalid_symbol = client.get("/mt5-demo/market-data/tick/GBPUSD")
        invalid_timeframe = client.get("/mt5-demo/market-data/candles/EURUSD/W1")
        passed = (
            invalid_symbol.status_code == 200
            and invalid_timeframe.status_code == 200
            and invalid_symbol.json()["status"] == "INVALID_SYMBOL"
            and invalid_timeframe.json()["status"] == "INVALID_TIMEFRAME"
            and safety_ok(invalid_symbol.json())
            and safety_ok(invalid_timeframe.json())
        )
        return show("Invalid symbols and timeframes are rejected safely", passed)
    except Exception as exc:
        return show("Invalid symbols and timeframes are rejected safely", False, str(exc))


def verify_no_order_send_added() -> bool:
    try:
        token = "mt5." + "order_send"
        allowed = [
            "backend/demo_execution/mt5_demo_executor.py",
            "backend/mt5_demo/guarded_demo_order_sender_service.py",
        ]
        order_matches = []
        for path in (PROJECT_ROOT / "backend").rglob("*.py"):
            if token in path.read_text(encoding="utf-8", errors="ignore"):
                order_matches.append(path.relative_to(PROJECT_ROOT).as_posix())
        return show(
            "No unrestricted mt5 order execution path was added",
            sorted(order_matches) == allowed,
            ", ".join(order_matches),
        )
    except Exception as exc:
        return show("No new mt5 order execution path was added", False, str(exc))


def main() -> int:
    print("Phase 15 Day 2 MT5 Market Data Verification")
    print("=" * 78)
    checks = [
        verify_files(),
        verify_routes_and_payloads(),
        verify_invalid_inputs(),
        verify_no_order_send_added(),
    ]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
