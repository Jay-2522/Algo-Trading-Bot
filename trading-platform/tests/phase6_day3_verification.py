import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def candle(time: str, open_: float, high: float, low: float, close: float, volume: float = 100.0) -> dict:
    return {"time": time, "open": open_, "high": high, "low": low, "close": close, "volume": volume}


def bullish_bos_fixture() -> list[dict]:
    return [
        candle("2026-01-02T00:00:00+00:00", 100, 101, 99, 100),
        candle("2026-01-02T01:00:00+00:00", 100, 102, 100, 101),
        candle("2026-01-02T02:00:00+00:00", 101, 103, 101, 102),
        candle("2026-01-02T03:00:00+00:00", 102, 110, 102, 104),
        candle("2026-01-02T04:00:00+00:00", 104, 106, 101, 105),
        candle("2026-01-02T05:00:00+00:00", 105, 107, 98, 106),
        candle("2026-01-02T06:00:00+00:00", 106, 108, 100, 107),
        candle("2026-01-02T07:00:00+00:00", 107, 109, 102, 108),
        candle("2026-01-02T08:00:00+00:00", 108, 112, 104, 111),
    ]


def bearish_bos_fixture() -> list[dict]:
    return [
        candle("2026-01-02T00:00:00+00:00", 110, 112, 109, 110),
        candle("2026-01-02T01:00:00+00:00", 110, 111, 108, 109),
        candle("2026-01-02T02:00:00+00:00", 109, 110, 107, 108),
        candle("2026-01-02T03:00:00+00:00", 108, 109, 100, 107),
        candle("2026-01-02T04:00:00+00:00", 107, 108, 104, 106),
        candle("2026-01-02T05:00:00+00:00", 106, 112, 103, 105),
        candle("2026-01-02T06:00:00+00:00", 105, 107, 102, 104),
        candle("2026-01-02T07:00:00+00:00", 104, 106, 101, 103),
        candle("2026-01-02T08:00:00+00:00", 103, 104, 98, 99),
    ]


def bullish_choch_fixture() -> list[dict]:
    candles = bearish_bos_fixture()
    candles[-1] = candle("2026-01-02T08:00:00+00:00", 103, 114, 102, 113)
    return candles


def bearish_choch_fixture() -> list[dict]:
    candles = bullish_bos_fixture()
    candles[-1] = candle("2026-01-02T08:00:00+00:00", 108, 109, 96, 97)
    return candles


def verify_files() -> bool:
    files = [
        "backend/strategy_engine/swing_point_detector.py",
        "backend/strategy_engine/bos_choch_detector.py",
        "backend/strategy_engine/structure_strength_scorer.py",
        "docs/phase-6-day-3-progress.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    return show("Swing, BOS/CHOCH, scorer, and docs files exist", not missing, ", ".join(missing))


def verify_model_fields() -> bool:
    try:
        from backend.strategy_engine.strategy_models import SMCStructureContext

        fields = set(SMCStructureContext.model_fields)
        expected = {
            "swing_highs",
            "swing_lows",
            "latest_swing_high",
            "latest_swing_low",
            "bos_direction",
            "choch_direction",
            "structure_shift_detected",
            "break_level",
            "break_price",
            "break_candle_time",
            "post_sweep_confirmation",
            "structure_strength",
            "structure_quality",
            "confirmation_reason",
        }
        return show("SMCStructureContext exposes Day 3 fields", expected <= fields)
    except Exception as exc:
        return show("SMCStructureContext exposes Day 3 fields", False, str(exc))


def verify_no_candle_placeholder() -> bool:
    try:
        from backend.strategy_engine.smc_structure_detector import SMCStructureDetector

        context = SMCStructureDetector().detect()
        passed = (
            context.bos_direction == "NONE"
            and context.choch_direction == "NONE"
            and context.structure_bias == "NEUTRAL"
            and context.structure_quality == "NONE"
            and context.warnings
        )
        return show("No-candle structure placeholder is safe", passed)
    except Exception as exc:
        return show("No-candle structure placeholder is safe", False, str(exc))


def verify_bos_choch_detection() -> bool:
    try:
        from backend.strategy_engine.smc_structure_detector import SMCStructureDetector

        detector = SMCStructureDetector()
        bullish_bos = detector.detect(candles=bullish_bos_fixture())
        bearish_bos = detector.detect(candles=bearish_bos_fixture())
        bullish_choch = detector.detect(candles=bullish_choch_fixture())
        bearish_choch = detector.detect(candles=bearish_choch_fixture())
        passed = (
            bullish_bos.bos_direction == "BULLISH_BOS"
            and bullish_bos.structure_bias == "BULLISH"
            and bearish_bos.bos_direction == "BEARISH_BOS"
            and bearish_bos.structure_bias == "BEARISH"
            and bullish_choch.choch_direction == "BULLISH_CHOCH"
            and bearish_choch.choch_direction == "BEARISH_CHOCH"
        )
        return show("Bullish/bearish BOS and CHOCH are detected", passed)
    except Exception as exc:
        return show("Bullish/bearish BOS and CHOCH are detected", False, str(exc))


def verify_post_sweep_confirmation_and_scoring() -> bool:
    try:
        from backend.strategy_engine.smc_structure_detector import SMCStructureDetector
        from backend.strategy_engine.strategy_models import LiquiditySweepContext

        detector = SMCStructureDetector()
        bullish = detector.detect(
            candles=bullish_bos_fixture(),
            liquidity_context=LiquiditySweepContext(symbol="XAUUSD", sweep_direction="SELL_SIDE_SWEEP"),
        )
        bearish = detector.detect(
            candles=bearish_bos_fixture(),
            liquidity_context=LiquiditySweepContext(symbol="XAUUSD", sweep_direction="BUY_SIDE_SWEEP"),
        )
        passed = (
            bullish.post_sweep_confirmation is True
            and bearish.post_sweep_confirmation is True
            and bullish.structure_strength > 0
            and bullish.confidence > 0
            and bullish.structure_quality in {"LOW", "MEDIUM", "HIGH"}
        )
        return show("Post-sweep confirmation and structure scoring work", passed)
    except Exception as exc:
        return show("Post-sweep confirmation and structure scoring work", False, str(exc))


def verify_strategy_and_routes() -> bool:
    try:
        from backend.main import app
        from backend.strategy_engine.xauusd_strategy_engine import XAUUSDStrategyEngine

        signal = XAUUSDStrategyEngine().analyze(candles=bullish_bos_fixture())
        client = TestClient(app)
        get_response = client.get("/strategy/structure/xauusd")
        post_response = client.post("/strategy/structure/xauusd/analyze", json={"candles": bullish_bos_fixture()})
        analyze_response = client.post("/strategy/analyze/xauusd", json={"candles": bullish_bos_fixture()})
        payload = post_response.json()
        signal_payload = analyze_response.json()
        passed = (
            signal.execution_allowed is False
            and get_response.status_code == 200
            and post_response.status_code == 200
            and analyze_response.status_code == 200
            and payload["bos_direction"] == "BULLISH_BOS"
            and payload["structure_bias"] == "BULLISH"
            and signal_payload["execution_allowed"] is False
            and "smc_context" in signal_payload
        )
        return show("Structure API routes and XAUUSD analysis route work", passed)
    except Exception as exc:
        return show("Structure API routes and XAUUSD analysis route work", False, str(exc))


def verify_order_send_isolated() -> bool:
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
        expected_phase6 = {
            "/strategy/status",
            "/strategy/analyze/xauusd",
            "/strategy/liquidity/xauusd",
            "/strategy/liquidity/xauusd/analyze",
            "/strategy/structure/xauusd",
            "/strategy/structure/xauusd/analyze",
            "/strategy/fvg/xauusd",
            "/strategy/fvg/xauusd/analyze",
            "/strategy/signals",
            "/strategy/signals/{signal_id}",
            "/strategy/session-context",
        }
        all_route_paths = {route.path for route in app.routes}
        missing = sorted(REQUIRED_GET_ROUTES - registered_get_routes)
        missing += sorted(expected_phase6 - all_route_paths)
        missing_ws = sorted(REQUIRED_WEBSOCKET_ROUTES - registered_websockets)
        return show("Phase 6 Day 1/2 and Phase 5 routes are preserved", not missing and not missing_ws, ", ".join(missing + missing_ws))
    except Exception as exc:
        return show("Phase 6 Day 1/2 and Phase 5 routes are preserved", False, str(exc))


def main() -> int:
    print("Phase 6 Day 3 BOS / CHOCH Structure Verification")
    print("=" * 60)
    checks = [
        verify_files(),
        verify_model_fields(),
        verify_no_candle_placeholder(),
        verify_bos_choch_detection(),
        verify_post_sweep_confirmation_and_scoring(),
        verify_strategy_and_routes(),
        verify_order_send_isolated(),
        verify_preserved_routes(),
    ]
    print("=" * 60)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
