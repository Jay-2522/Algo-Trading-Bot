import sys
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


REQUIRED_FILES = [
    "backend/mt5_demo/mt5_historical_backfill_service.py",
    "backend/mt5_demo/mt5_strategy_feed_adapter.py",
    "backend/api/mt5_demo_routes.py",
    "docs/phase15-day4-mt5-historical-backfill-strategy-feed.md",
]

REQUIRED_ROUTE_PATTERNS = {
    "/mt5-demo/history/status",
    "/mt5-demo/history/{symbol}/{timeframe}",
    "/mt5-demo/history/{symbol}/{timeframe}/summary",
    "/mt5-demo/history/{symbol}/{timeframe}/validate",
    "/mt5-demo/strategy-feed/{symbol}",
    "/mt5-demo/strategy-feed/{symbol}/htf",
    "/mt5-demo/strategy-feed/{symbol}/ltf",
}

HISTORY_PATHS = [
    "/mt5-demo/history/EURUSD/M5",
    "/mt5-demo/history/EURUSD/H1",
    "/mt5-demo/history/EURUSD/H4",
    "/mt5-demo/history/XAUUSD/M5",
    "/mt5-demo/history/XAUUSD/H1",
    "/mt5-demo/history/XAUUSD/H4",
]

SUMMARY_PATHS = [
    "/mt5-demo/history/EURUSD/H1/summary",
    "/mt5-demo/history/XAUUSD/H1/summary",
]

VALIDATE_PATHS = [
    "/mt5-demo/history/EURUSD/H1/validate",
    "/mt5-demo/history/XAUUSD/H1/validate",
]

FEED_PATHS = [
    "/mt5-demo/strategy-feed/EURUSD",
    "/mt5-demo/strategy-feed/XAUUSD",
    "/mt5-demo/strategy-feed/EURUSD/htf",
    "/mt5-demo/strategy-feed/XAUUSD/htf",
    "/mt5-demo/strategy-feed/EURUSD/ltf",
    "/mt5-demo/strategy-feed/XAUUSD/ltf",
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


def no_fake_candles(payload: Any) -> bool:
    for key, value in walk(payload):
        key_text = str(key).lower()
        value_text = str(value).lower()
        if key_text in {"placeholder", "validation_sample", "sample_data_used"} and value:
            return False
        if "fake candle" in value_text or "sample candle" in value_text:
            return False
    return True


def verify_files() -> bool:
    missing = [path for path in REQUIRED_FILES if not (PROJECT_ROOT / path).is_file()]
    return show("Historical backfill service, strategy feed adapter, routes, and docs exist", not missing, ", ".join(missing))


def verify_routes_and_history() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        route_paths = {route.path for route in app.routes if hasattr(route, "methods")}
        missing = sorted(REQUIRED_ROUTE_PATTERNS - route_paths)
        responses = [client.get("/mt5-demo/history/status")]
        responses.extend(client.get(path) for path in HISTORY_PATHS)
        responses.extend(client.get(path) for path in SUMMARY_PATHS)
        responses.extend(client.get(path) for path in VALIDATE_PATHS)
        payloads = [response.json() for response in responses]
        allowed_statuses = {
            "OK",
            "MT5_UNAVAILABLE",
            "SYMBOL_UNAVAILABLE",
            "CANDLES_UNAVAILABLE",
            "CANDLE_READ_FAILED",
            "HISTORY_UNAVAILABLE",
            "INVALID_SYMBOL",
            "INVALID_TIMEFRAME",
        }
        history_ok = all(
            payload.get("symbol") in {"EURUSD", "XAUUSD"}
            and payload.get("timeframe") in {"M5", "H1", "H4"}
            and payload.get("status") in allowed_statuses
            and isinstance(payload.get("candles"), list)
            and isinstance(payload.get("validation"), dict)
            and no_fake_candles(payload)
            for payload in payloads[1:7]
        )
        summary_ok = all(
            payload.get("symbol") in {"EURUSD", "XAUUSD"}
            and payload.get("timeframe") == "H1"
            and payload.get("status") in allowed_statuses
            and isinstance(payload.get("validation"), dict)
            for payload in payloads[7:9]
        )
        validate_ok = all(
            payload.get("symbol") in {"EURUSD", "XAUUSD"}
            and payload.get("timeframe") == "H1"
            and payload.get("status") in allowed_statuses
            and isinstance(payload.get("validation"), dict)
            for payload in payloads[9:11]
        )
        passed = (
            not missing
            and all(response.status_code == 200 for response in responses)
            and payloads[0]["status"] == "HISTORICAL_BACKFILL_READY"
            and history_ok
            and summary_ok
            and validate_ok
            and all(safety_ok(payload) for payload in payloads)
        )
        return show("Historical backfill routes work safely", passed, ", ".join(missing))
    except Exception as exc:
        return show("Historical backfill routes work safely", False, str(exc))


def verify_strategy_feed() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        responses = [client.get(path) for path in FEED_PATHS]
        payloads = [response.json() for response in responses]
        passed = (
            all(response.status_code == 200 for response in responses)
            and all(payload.get("symbol") in {"EURUSD", "XAUUSD"} for payload in payloads)
            and all(payload.get("source") == "MT5_DEMO_HISTORY" for payload in payloads)
            and all(payload.get("feed_ready") in {True, False} for payload in payloads)
            and all(isinstance(payload.get("warnings"), list) for payload in payloads)
            and all(payload.get("forced_signal", False) is False for payload in payloads[:2])
            and all(payload.get("execution_triggered", False) is False for payload in payloads[:2])
            and all(safety_ok(payload) and no_fake_candles(payload) for payload in payloads)
        )
        return show("Strategy feed routes build or safely report not ready", passed)
    except Exception as exc:
        return show("Strategy feed routes build or safely report not ready", False, str(exc))


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
    print("Phase 15 Day 4 MT5 Historical Backfill Verification")
    print("=" * 78)
    checks = [
        verify_files(),
        verify_routes_and_history(),
        verify_strategy_feed(),
        verify_no_order_send_added(),
    ]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
