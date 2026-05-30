import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def candle(time: str, open_: float, high: float, low: float, close: float, volume: float = 100.0) -> dict:
    return {
        "time": time,
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    }


def buy_side_sweep_fixture(sweep_time: str = "2026-01-02T08:00:00+00:00") -> list[dict]:
    return [
        candle("2026-01-01T08:00:00+00:00", 2338, 2345, 2332, 2340, 100),
        candle("2026-01-01T12:00:00+00:00", 2340, 2348, 2336, 2342, 100),
        candle("2026-01-02T00:00:00+00:00", 2335, 2344, 2330, 2338, 100),
        candle("2026-01-02T02:00:00+00:00", 2338, 2348, 2334, 2344, 100),
        candle("2026-01-02T04:00:00+00:00", 2344, 2350, 2338, 2347, 100),
        candle("2026-01-02T06:00:00+00:00", 2347, 2350, 2340, 2346, 100),
        candle(sweep_time, 2349, 2352, 2346, 2348, 180),
    ]


def sell_side_sweep_fixture(sweep_time: str = "2026-01-02T13:00:00+00:00") -> list[dict]:
    return [
        candle("2026-01-01T08:00:00+00:00", 2336, 2342, 2325, 2330, 100),
        candle("2026-01-01T12:00:00+00:00", 2330, 2338, 2322, 2328, 100),
        candle("2026-01-02T00:00:00+00:00", 2330, 2336, 2324, 2332, 100),
        candle("2026-01-02T02:00:00+00:00", 2332, 2337, 2320, 2326, 100),
        candle("2026-01-02T04:00:00+00:00", 2326, 2331, 2320, 2324, 100),
        candle("2026-01-02T06:00:00+00:00", 2324, 2330, 2322, 2325, 100),
        candle(sweep_time, 2321, 2326, 2318, 2322, 180),
    ]


def equal_highs_fixture() -> list[dict]:
    return [
        candle("2026-01-01T08:00:00+00:00", 2330, 2342.0, 2324, 2334),
        candle("2026-01-01T10:00:00+00:00", 2334, 2342.1, 2328, 2338),
        candle("2026-01-02T00:00:00+00:00", 2338, 2340, 2330, 2335),
        candle("2026-01-02T02:00:00+00:00", 2335, 2342.05, 2331, 2338),
        candle("2026-01-02T08:00:00+00:00", 2341, 2343, 2336, 2341.5),
    ]


def verify_files() -> bool:
    files = [
        "backend/strategy_engine/liquidity_level_builder.py",
        "backend/strategy_engine/sweep_strength_scorer.py",
        "docs/phase-6-day-2-progress.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    return show("Liquidity level builder, scorer, and docs exist", not missing, ", ".join(missing))


def verify_model_fields() -> bool:
    try:
        from backend.strategy_engine.strategy_models import LiquiditySweepContext

        fields = set(LiquiditySweepContext.model_fields)
        expected = {
            "equal_highs",
            "equal_lows",
            "liquidity_pools",
            "active_sweep_level",
            "sweep_price",
            "rejection_detected",
            "rejection_candle_type",
            "sweep_strength",
            "sweep_quality",
            "session_alignment",
            "volume_spike_detected",
            "structure_confirmation_pending",
        }
        return show("LiquiditySweepContext exposes Day 2 fields", expected <= fields)
    except Exception as exc:
        return show("LiquiditySweepContext exposes Day 2 fields", False, str(exc))


def verify_no_candle_placeholder() -> bool:
    try:
        from backend.strategy_engine.liquidity_sweep_detector import LiquiditySweepDetector

        context = LiquiditySweepDetector().detect()
        passed = (
            context.sweep_direction == "NONE"
            and context.confidence == 0.0
            and context.sweep_strength == 0.0
            and context.sweep_quality == "NONE"
            and context.warnings
        )
        return show("No-candle liquidity placeholder is safe", passed)
    except Exception as exc:
        return show("No-candle liquidity placeholder is safe", False, str(exc))


def verify_buy_side_sweep() -> bool:
    try:
        from backend.strategy_engine.liquidity_sweep_detector import LiquiditySweepDetector

        context = LiquiditySweepDetector().detect(candles=buy_side_sweep_fixture())
        passed = (
            context.asian_high == 2350
            and context.sweep_direction == "BUY_SIDE_SWEEP"
            and context.rejection_detected is True
            and context.sweep_price == 2352
            and context.sweep_strength > 0
            and context.confidence > 0
        )
        return show("Buy-side sweep above Asian/previous high is detected", passed)
    except Exception as exc:
        return show("Buy-side sweep above Asian/previous high is detected", False, str(exc))


def verify_sell_side_sweep() -> bool:
    try:
        from backend.strategy_engine.liquidity_sweep_detector import LiquiditySweepDetector

        context = LiquiditySweepDetector().detect(candles=sell_side_sweep_fixture())
        passed = (
            context.asian_low == 2320
            and context.sweep_direction == "SELL_SIDE_SWEEP"
            and context.rejection_detected is True
            and context.sweep_price == 2318
            and context.sweep_strength > 0
            and context.confidence > 0
        )
        return show("Sell-side sweep below Asian/previous low is detected", passed)
    except Exception as exc:
        return show("Sell-side sweep below Asian/previous low is detected", False, str(exc))


def verify_equal_levels() -> bool:
    try:
        from backend.strategy_engine.liquidity_level_builder import LiquidityLevelBuilder

        levels = LiquidityLevelBuilder().build_levels(candles=equal_highs_fixture())
        passed = (
            len(levels["equal_highs"]) > 0
            and any(pool["type"] == "EQUAL_HIGHS" for pool in levels["liquidity_pools"])
        )
        return show("Equal highs and liquidity pools are identified", passed)
    except Exception as exc:
        return show("Equal highs and liquidity pools are identified", False, str(exc))


def verify_session_scoring() -> bool:
    try:
        from backend.strategy_engine.liquidity_sweep_detector import LiquiditySweepDetector

        detector = LiquiditySweepDetector()
        london = detector.detect(candles=buy_side_sweep_fixture("2026-01-02T08:00:00+00:00"))
        off_session = detector.detect(candles=buy_side_sweep_fixture("2026-01-02T22:00:00+00:00"))
        passed = (
            london.session_alignment is True
            and off_session.session_alignment is False
            and london.sweep_strength > off_session.sweep_strength
            and london.sweep_quality in {"HIGH", "MEDIUM"}
            and off_session.sweep_quality in {"MEDIUM", "LOW"}
        )
        return show("London/NY sweeps score higher than off-session sweeps", passed)
    except Exception as exc:
        return show("London/NY sweeps score higher than off-session sweeps", False, str(exc))


def verify_strategy_integration() -> bool:
    try:
        from backend.strategy_engine.xauusd_strategy_engine import XAUUSDStrategyEngine

        signal = XAUUSDStrategyEngine().analyze(candles=buy_side_sweep_fixture())
        passed = (
            signal.action == "WAIT"
            and signal.execution_allowed is False
            and signal.liquidity_context.sweep_direction == "BUY_SIDE_SWEEP"
            and signal.liquidity_context.rejection_detected is True
            and "Structure bos=" in signal.reason
            and "Waiting because" in signal.reason
        )
        return show("Strategy engine consumes improved liquidity context without issuing trade signals", passed)
    except Exception as exc:
        return show("Strategy engine consumes improved liquidity context without issuing trade signals", False, str(exc))


def verify_routes() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        get_response = client.get("/strategy/liquidity/xauusd")
        post_response = client.post("/strategy/liquidity/xauusd/analyze", json={"candles": buy_side_sweep_fixture()})
        analyze_response = client.post("/strategy/analyze/xauusd", json={"candles": buy_side_sweep_fixture()})
        payload = post_response.json()
        signal_payload = analyze_response.json()
        passed = (
            get_response.status_code == 200
            and post_response.status_code == 200
            and analyze_response.status_code == 200
            and payload["sweep_direction"] == "BUY_SIDE_SWEEP"
            and payload["rejection_detected"] is True
            and signal_payload["execution_allowed"] is False
        )
        return show("Liquidity API routes and XAUUSD analysis route work", passed)
    except Exception as exc:
        return show("Liquidity API routes and XAUUSD analysis route work", False, str(exc))


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
        all_route_paths = {route.path for route in app.routes}
        expected_day1 = {
            "/strategy/status",
            "/strategy/analyze/xauusd",
            "/strategy/signals",
            "/strategy/signals/{signal_id}",
            "/strategy/session-context",
            "/strategy/structure/xauusd",
            "/strategy/structure/xauusd/analyze",
            "/strategy/fvg/xauusd",
            "/strategy/fvg/xauusd/analyze",
        }
        missing = sorted(REQUIRED_GET_ROUTES - registered_get_routes)
        missing += sorted(expected_day1 - all_route_paths)
        missing_ws = sorted(REQUIRED_WEBSOCKET_ROUTES - registered_websockets)
        return show("Phase 6 Day 1 and Phase 5 routes are preserved", not missing and not missing_ws, ", ".join(missing + missing_ws))
    except Exception as exc:
        return show("Phase 6 Day 1 and Phase 5 routes are preserved", False, str(exc))


def main() -> int:
    print("Phase 6 Day 2 XAUUSD Liquidity Sweep Verification")
    print("=" * 60)
    checks = [
        verify_files(),
        verify_model_fields(),
        verify_no_candle_placeholder(),
        verify_buy_side_sweep(),
        verify_sell_side_sweep(),
        verify_equal_levels(),
        verify_session_scoring(),
        verify_strategy_integration(),
        verify_routes(),
        verify_order_send_isolated(),
        verify_preserved_routes(),
    ]
    print("=" * 60)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
