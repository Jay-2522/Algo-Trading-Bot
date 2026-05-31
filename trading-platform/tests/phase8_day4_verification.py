import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def candle(hour, open_, high, low, close):
    time = datetime(2026, 5, 30, hour, 0, tzinfo=timezone.utc)
    return {
        "time": time.isoformat().replace("+00:00", "Z"),
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
    }


def bullish_fvg_fixture():
    return [
        candle(7, 1.0790, 1.0800, 1.0788, 1.0795),
        candle(8, 1.0795, 1.0812, 1.0794, 1.0810),
        candle(9, 1.0810, 1.0820, 1.0804, 1.0816),
    ]


def bearish_fvg_fixture():
    return [
        candle(7, 1.0860, 1.0864, 1.0850, 1.0855),
        candle(8, 1.0855, 1.0857, 1.0838, 1.0840),
        candle(9, 1.0840, 1.0846, 1.0830, 1.0835),
    ]


def tiny_gap_fixture():
    return [
        candle(7, 1.0790, 1.08000, 1.0788, 1.0795),
        candle(8, 1.0795, 1.0805, 1.0794, 1.0804),
        candle(9, 1.0804, 1.0810, 1.08005, 1.0806),
    ]


def mitigated_fvg_fixture():
    return bullish_fvg_fixture() + [candle(10, 1.0816, 1.0818, 1.0800, 1.0805)]


def verify_files_and_models() -> bool:
    files = [
        "backend/strategy_engine/eurusd_fvg_engine.py",
        "docs/phase-8-day-4-progress.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    try:
        from backend.strategy_engine.strategy_models import EURUSDFVGContext, EURUSDFairValueGap, EURUSDStrategySignal

        model_ok = (
            "fvg_id" in EURUSDFairValueGap.model_fields
            and "midpoint" in EURUSDFairValueGap.model_fields
            and "fair_value_gaps" in EURUSDFVGContext.model_fields
            and "fvg_context" in EURUSDStrategySignal.model_fields
        )
    except Exception:
        model_ok = False
    return show("EURUSD FVG engine, docs, and models exist", not missing and model_ok, ", ".join(missing))


def verify_fvg_engine() -> bool:
    try:
        from backend.strategy_engine.eurusd_fvg_engine import EURUSDFVGEngine

        engine = EURUSDFVGEngine()
        empty = engine.detect()
        bullish = engine.detect(bullish_fvg_fixture())
        bearish = engine.detect(bearish_fvg_fixture())
        tiny = engine.detect(tiny_gap_fixture())
        mitigated = engine.detect(mitigated_fvg_fixture())
        structure_aligned = engine.detect(
            bullish_fvg_fixture(),
            structure_context={"structure_bias": "BULLISH", "bos_direction": "BULLISH_BOS"},
        )
        liquidity_aligned = engine.detect(
            bullish_fvg_fixture(),
            liquidity_context={"sweep_direction": "SELL_SIDE_SWEEP"},
        )
        latest_bullish = bullish.latest_fvg
        latest_bearish = bearish.latest_fvg
        passed = (
            engine.tolerance == 0.0002
            and engine.min_gap_size == 0.0001
            and empty.active_fvg_detected is False
            and empty.fvg_direction == "NONE"
            and empty.warnings
            and latest_bullish is not None
            and latest_bullish.direction == "BULLISH"
            and latest_bullish.lower_bound == 1.08
            and latest_bullish.upper_bound == 1.0804
            and latest_bullish.midpoint == 1.0802
            and latest_bearish is not None
            and latest_bearish.direction == "BEARISH"
            and latest_bearish.upper_bound == 1.085
            and latest_bearish.lower_bound == 1.0846
            and latest_bearish.midpoint == 1.0848
            and tiny.fair_value_gaps == []
            and mitigated.latest_fvg is not None
            and mitigated.latest_fvg.mitigated is True
            and structure_aligned.latest_fvg is not None
            and structure_aligned.latest_fvg.aligned_with_structure is True
            and liquidity_aligned.latest_fvg is not None
            and liquidity_aligned.latest_fvg.aligned_with_liquidity is True
        )
        return show("EURUSD FVG detection, midpoint, threshold, mitigation, and alignment work", passed)
    except Exception as exc:
        return show("EURUSD FVG detection, midpoint, threshold, mitigation, and alignment work", False, str(exc))


def verify_routes_and_strategy() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        placeholder = client.get("/strategy/eurusd/fvg")
        analyzed = client.post("/strategy/eurusd/fvg/analyze", json={"candles": bullish_fvg_fixture()})
        signal = client.post("/strategy/analyze/eurusd", json={"candles": bullish_fvg_fixture()})
        payload = signal.json()
        passed = (
            placeholder.status_code == 200
            and placeholder.json()["symbol"] == "EURUSD"
            and placeholder.json()["active_fvg_detected"] is False
            and analyzed.status_code == 200
            and analyzed.json()["fvg_direction"] == "BULLISH"
            and signal.status_code == 200
            and payload["symbol"] == "EURUSD"
            and payload["action"] == "WAIT"
            and payload["execution_allowed"] is False
            and "fvg_context" in payload
            and payload["fvg_context"]["fvg_direction"] == "BULLISH"
            and payload["metadata"]["phase"] in {"PHASE_8_DAY_4", "PHASE_8_DAY_5", "PHASE_8_DAY_6", "PHASE_8_DAY_7"}
            and payload["metadata"]["fvg_engine_integrated"] is True
            and payload["metadata"]["simulation_only"] is True
            and payload["metadata"]["live_execution_enabled"] is False
        )
        return show("EURUSD FVG routes and strategy integration work", passed)
    except Exception as exc:
        return show("EURUSD FVG routes and strategy integration work", False, str(exc))


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
            "/strategy/eurusd/structure",
            "/strategy/eurusd/fvg",
            "/strategy/confluence/xauusd",
            "/strategy/fvg/xauusd",
            "/news/phase7/status",
            "/news/command-center",
        }
        missing = sorted((REQUIRED_GET_ROUTES | expected) - registered_get_routes)
        missing_ws = sorted(REQUIRED_WEBSOCKET_ROUTES - registered_websockets)
        return show("Phase 8 Day 1-3, XAUUSD, and Phase 7 routes are preserved", not missing and not missing_ws, ", ".join(missing + missing_ws))
    except Exception as exc:
        return show("Phase 8 Day 1-3, XAUUSD, and Phase 7 routes are preserved", False, str(exc))


def main() -> int:
    print("Phase 8 Day 4 EURUSD Fair Value Gap Verification")
    print("=" * 61)
    checks = [
        verify_files_and_models(),
        verify_fvg_engine(),
        verify_routes_and_strategy(),
        verify_no_order_send_added(),
        verify_preserved_routes(),
    ]
    print("=" * 61)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
