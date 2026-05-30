import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def candle(time: str, open_: float, high: float, low: float, close: float) -> dict:
    return {"time": time, "open": open_, "high": high, "low": low, "close": close, "volume": 100}


def bullish_fvg_fixture(extra: list[dict] | None = None) -> list[dict]:
    candles = [
        candle("2026-01-02T07:00:00+00:00", 2312, 2320, 2310, 2318),
        candle("2026-01-02T08:00:00+00:00", 2318, 2332, 2316, 2330),
        candle("2026-01-02T09:00:00+00:00", 2330, 2338, 2325, 2336),
    ]
    return candles + (extra or [])


def bearish_fvg_fixture(extra: list[dict] | None = None) -> list[dict]:
    candles = [
        candle("2026-01-02T07:00:00+00:00", 2350, 2355, 2340, 2345),
        candle("2026-01-02T08:00:00+00:00", 2345, 2348, 2328, 2330),
        candle("2026-01-02T09:00:00+00:00", 2330, 2335, 2322, 2326),
    ]
    return candles + (extra or [])


def verify_files() -> bool:
    files = [
        "backend/strategy_engine/fvg_detector.py",
        "backend/strategy_engine/fvg_quality_scorer.py",
        "docs/phase-6-day-4-progress.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    return show("FVG detector, scorer, and docs files exist", not missing, ", ".join(missing))


def verify_models() -> bool:
    try:
        from backend.strategy_engine.strategy_models import FairValueGap, SMCStructureContext

        fvg_fields = set(FairValueGap.model_fields)
        smc_fields = set(SMCStructureContext.model_fields)
        expected_fvg = {
            "fvg_id",
            "symbol",
            "direction",
            "start_time",
            "end_time",
            "upper_bound",
            "lower_bound",
            "midpoint",
            "size",
            "fill_percentage",
            "mitigated",
            "active",
            "displacement_strength",
            "quality",
            "aligned_with_structure",
            "aligned_with_liquidity",
            "warnings",
        }
        expected_smc = {
            "fair_value_gaps",
            "latest_fvg",
            "bullish_fvg_detected",
            "bearish_fvg_detected",
            "active_fvg_detected",
            "fvg_direction",
            "fvg_quality",
            "fvg_confidence",
            "fvg_alignment_reason",
        }
        return show("FairValueGap model and SMC FVG fields exist", expected_fvg <= fvg_fields and expected_smc <= smc_fields)
    except Exception as exc:
        return show("FairValueGap model and SMC FVG fields exist", False, str(exc))


def verify_no_candle_placeholder() -> bool:
    try:
        from backend.strategy_engine.smc_structure_detector import SMCStructureDetector

        context = SMCStructureDetector().detect()
        passed = (
            context.fair_value_gaps == []
            and context.active_fvg_detected is False
            and context.fvg_quality == "NONE"
            and context.warnings
        )
        return show("No-candle FVG placeholder is safe", passed)
    except Exception as exc:
        return show("No-candle FVG placeholder is safe", False, str(exc))


def verify_bullish_bearish_fvgs() -> bool:
    try:
        from backend.strategy_engine.fvg_detector import FairValueGapDetector

        bullish = FairValueGapDetector().detect(candles=bullish_fvg_fixture())["latest_fvg"]
        bearish = FairValueGapDetector().detect(candles=bearish_fvg_fixture())["latest_fvg"]
        passed = (
            bullish is not None
            and bullish.direction == "BULLISH"
            and bullish.lower_bound == 2320
            and bullish.upper_bound == 2325
            and bullish.midpoint == 2322.5
            and bearish is not None
            and bearish.direction == "BEARISH"
            and bearish.upper_bound == 2340
            and bearish.lower_bound == 2335
            and bearish.midpoint == 2337.5
        )
        return show("Bullish and bearish FVGs with midpoint are detected", passed)
    except Exception as exc:
        return show("Bullish and bearish FVGs with midpoint are detected", False, str(exc))


def verify_fill_and_mitigation() -> bool:
    try:
        from backend.strategy_engine.fvg_detector import FairValueGapDetector

        partial = FairValueGapDetector().detect(
            candles=bullish_fvg_fixture([candle("2026-01-02T10:00:00+00:00", 2330, 2332, 2322.5, 2328)])
        )["latest_fvg"]
        mitigated = FairValueGapDetector().detect(
            candles=bullish_fvg_fixture([candle("2026-01-02T10:00:00+00:00", 2330, 2332, 2319, 2321)])
        )["latest_fvg"]
        passed = (
            partial is not None
            and partial.fill_percentage > 0
            and partial.mitigated is False
            and mitigated is not None
            and mitigated.fill_percentage == 100.0
            and mitigated.mitigated is True
            and mitigated.active is False
        )
        return show("FVG fill percentage, mitigated, and active state work", passed)
    except Exception as exc:
        return show("FVG fill percentage, mitigated, and active state work", False, str(exc))


def verify_alignment() -> bool:
    try:
        from backend.strategy_engine.fvg_detector import FairValueGapDetector
        from backend.strategy_engine.strategy_models import LiquiditySweepContext, SMCStructureContext

        structure = SMCStructureContext(symbol="XAUUSD", bos_direction="BULLISH_BOS", structure_bias="BULLISH")
        liquidity = LiquiditySweepContext(symbol="XAUUSD", sweep_direction="SELL_SIDE_SWEEP")
        fvg = FairValueGapDetector().detect(
            candles=bullish_fvg_fixture(),
            structure_context=structure,
            liquidity_context=liquidity,
        )["latest_fvg"]
        passed = (
            fvg is not None
            and fvg.aligned_with_structure is True
            and fvg.aligned_with_liquidity is True
            and fvg.quality in {"MEDIUM", "HIGH"}
        )
        return show("FVG structure and liquidity alignment work", passed)
    except Exception as exc:
        return show("FVG structure and liquidity alignment work", False, str(exc))


def verify_routes_and_strategy() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        get_response = client.get("/strategy/fvg/xauusd")
        post_response = client.post("/strategy/fvg/xauusd/analyze", json={"candles": bullish_fvg_fixture()})
        analyze_response = client.post("/strategy/analyze/xauusd", json={"candles": bullish_fvg_fixture()})
        payload = post_response.json()
        signal_payload = analyze_response.json()
        passed = (
            get_response.status_code == 200
            and post_response.status_code == 200
            and analyze_response.status_code == 200
            and payload["latest_fvg"]["direction"] == "BULLISH"
            and payload["active_fvg_detected"] is True
            and signal_payload["execution_allowed"] is False
            and "smc_context" in signal_payload
        )
        return show("FVG API routes and XAUUSD analysis route work", passed)
    except Exception as exc:
        return show("FVG API routes and XAUUSD analysis route work", False, str(exc))


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
        return show("Phase 6 Day 1-3 and Phase 5 routes are preserved", not missing and not missing_ws, ", ".join(missing + missing_ws))
    except Exception as exc:
        return show("Phase 6 Day 1-3 and Phase 5 routes are preserved", False, str(exc))


def main() -> int:
    print("Phase 6 Day 4 Fair Value Gap Verification")
    print("=" * 54)
    checks = [
        verify_files(),
        verify_models(),
        verify_no_candle_placeholder(),
        verify_bullish_bearish_fvgs(),
        verify_fill_and_mitigation(),
        verify_alignment(),
        verify_routes_and_strategy(),
        verify_order_send_isolated(),
        verify_preserved_routes(),
    ]
    print("=" * 54)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
