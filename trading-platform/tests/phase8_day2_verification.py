import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def candle(time, open_, high, low, close):
    return {
        "time": time.isoformat().replace("+00:00", "Z"),
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
    }


def base_asian_candles():
    start = datetime(2026, 5, 30, 0, 0, tzinfo=timezone.utc)
    return [
        candle(start + timedelta(hours=0), 1.0820, 1.0830, 1.0810, 1.0824),
        candle(start + timedelta(hours=1), 1.0824, 1.0840, 1.0815, 1.0836),
        candle(start + timedelta(hours=2), 1.0836, 1.0850, 1.0825, 1.0840),
        candle(start + timedelta(hours=3), 1.0840, 1.0848, 1.0800, 1.0810),
        candle(start + timedelta(hours=4), 1.0810, 1.0835, 1.0804, 1.0820),
    ]


def buy_side_fixture():
    latest_time = datetime(2026, 5, 30, 8, 0, tzinfo=timezone.utc)
    return base_asian_candles() + [candle(latest_time, 1.0846, 1.0854, 1.0842, 1.0848)]


def sell_side_fixture():
    latest_time = datetime(2026, 5, 30, 8, 0, tzinfo=timezone.utc)
    return base_asian_candles() + [candle(latest_time, 1.0804, 1.0810, 1.0796, 1.0803)]


def equal_highs_fixture():
    start = datetime(2026, 5, 30, 0, 0, tzinfo=timezone.utc)
    return [
        candle(start + timedelta(hours=0), 1.0850, 1.0870, 1.0848, 1.0860),
        candle(start + timedelta(hours=1), 1.0860, 1.0871, 1.0852, 1.0863),
        candle(start + timedelta(hours=2), 1.0863, 1.0869, 1.0854, 1.0861),
        candle(start + timedelta(hours=8), 1.0861, 1.0865, 1.0857, 1.0860),
    ]


def verify_files_and_model() -> bool:
    files = [
        "backend/strategy_engine/eurusd_liquidity_engine.py",
        "docs/phase-8-day-2-progress.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    try:
        from backend.strategy_engine.strategy_models import EURUSDLiquidityContext, EURUSDStrategySignal

        model_ok = (
            "asian_high" in EURUSDLiquidityContext.model_fields
            and "sweep_direction" in EURUSDLiquidityContext.model_fields
            and "liquidity_context" in EURUSDStrategySignal.model_fields
        )
    except Exception:
        model_ok = False
    return show("EURUSD liquidity engine, docs, and model exist", not missing and model_ok, ", ".join(missing))


def verify_liquidity_engine() -> bool:
    try:
        from backend.strategy_engine.eurusd_liquidity_engine import EURUSDLiquidityEngine

        engine = EURUSDLiquidityEngine()
        empty = engine.detect()
        buy = engine.detect(buy_side_fixture())
        sell = engine.detect(sell_side_fixture())
        equal = engine.detect(equal_highs_fixture())
        passed = (
            engine.tolerance == 0.0002
            and empty.sweep_direction == "NONE"
            and empty.confidence == 0
            and empty.warnings
            and buy.asian_high == 1.085
            and buy.sweep_direction == "BUY_SIDE_SWEEP"
            and buy.rejection_detected is True
            and buy.active_sweep_level == "ASIAN_HIGH"
            and buy.confidence > 0
            and sell.asian_low == 1.08
            and sell.sweep_direction == "SELL_SIDE_SWEEP"
            and sell.rejection_detected is True
            and sell.active_sweep_level == "ASIAN_LOW"
            and sell.confidence > 0
            and len(equal.equal_highs) > 0
        )
        return show("EURUSD liquidity no-candle, sweep, equal-level, confidence, and tolerance rules work", passed)
    except Exception as exc:
        return show("EURUSD liquidity no-candle, sweep, equal-level, confidence, and tolerance rules work", False, str(exc))


def verify_routes_and_strategy() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        liquidity = client.get("/strategy/eurusd/liquidity")
        analyzed_liquidity = client.post("/strategy/eurusd/liquidity/analyze", json={"candles": buy_side_fixture()})
        signal = client.post("/strategy/analyze/eurusd", json={"candles": buy_side_fixture()})
        payload = signal.json()
        passed = (
            liquidity.status_code == 200
            and liquidity.json()["symbol"] == "EURUSD"
            and liquidity.json()["sweep_direction"] == "NONE"
            and analyzed_liquidity.status_code == 200
            and analyzed_liquidity.json()["sweep_direction"] == "BUY_SIDE_SWEEP"
            and signal.status_code == 200
            and payload["symbol"] == "EURUSD"
            and payload["action"] == "WAIT"
            and payload["execution_allowed"] is False
            and "liquidity_context" in payload
            and payload["liquidity_context"]["sweep_direction"] == "BUY_SIDE_SWEEP"
            and payload["metadata"]["phase"] in {"PHASE_8_DAY_2", "PHASE_8_DAY_3", "PHASE_8_DAY_4", "PHASE_8_DAY_5"}
            and payload["metadata"]["liquidity_engine_integrated"] is True
            and payload["metadata"]["simulation_only"] is True
            and payload["metadata"]["live_execution_enabled"] is False
        )
        return show("EURUSD liquidity routes and strategy integration work", passed)
    except Exception as exc:
        return show("EURUSD liquidity routes and strategy integration work", False, str(exc))


def verify_no_order_send_added() -> bool:
    token = "mt5." + "order_send"
    matches = []
    for path in (PROJECT_ROOT / "backend").rglob("*.py"):
        if path.is_file() and token in path.read_text(encoding="utf-8", errors="ignore"):
            matches.append(path.relative_to(PROJECT_ROOT).as_posix())
    passed = matches == ["backend/demo_execution/mt5_demo_executor.py"]
    return show("MT5 order submission remains isolated to guarded demo executor", passed, ", ".join(matches))


def verify_preserved_routes() -> bool:
    try:
        from backend.main import app
        from tests.regression_routes_verification import REQUIRED_GET_ROUTES, REQUIRED_WEBSOCKET_ROUTES

        registered_get_routes = {
            route.path
            for route in app.routes
            if hasattr(route, "methods") and "GET" in route.methods
        }
        registered_websockets = {
            route.path
            for route in app.routes
            if route.__class__.__name__ == "APIWebSocketRoute"
        }
        expected = {
            "/strategy/analyze/eurusd",
            "/strategy/eurusd/session-context",
            "/strategy/eurusd/indicator-context",
            "/strategy/eurusd/liquidity",
            "/strategy/confluence/xauusd",
            "/strategy/liquidity/xauusd",
            "/news/phase7/status",
            "/news/command-center",
        }
        missing = sorted((REQUIRED_GET_ROUTES | expected) - registered_get_routes)
        missing_ws = sorted(REQUIRED_WEBSOCKET_ROUTES - registered_websockets)
        return show("Phase 8 Day 1, XAUUSD, and Phase 7 routes are preserved", not missing and not missing_ws, ", ".join(missing + missing_ws))
    except Exception as exc:
        return show("Phase 8 Day 1, XAUUSD, and Phase 7 routes are preserved", False, str(exc))


def main() -> int:
    print("Phase 8 Day 2 EURUSD Liquidity Sweep Verification")
    print("=" * 62)
    checks = [
        verify_files_and_model(),
        verify_liquidity_engine(),
        verify_routes_and_strategy(),
        verify_no_order_send_added(),
        verify_preserved_routes(),
    ]
    print("=" * 62)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
