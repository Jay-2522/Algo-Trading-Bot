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


def bullish_order_block_fixture(extra: list[dict] | None = None) -> list[dict]:
    candles = [
        candle("2026-01-02T00:00:00+00:00", 100, 101, 99, 100),
        candle("2026-01-02T01:00:00+00:00", 100, 102, 100, 101),
        candle("2026-01-02T02:00:00+00:00", 101, 103, 101, 102),
        candle("2026-01-02T03:00:00+00:00", 102, 110, 102, 104),
        candle("2026-01-02T04:00:00+00:00", 104, 106, 101, 105),
        candle("2026-01-02T05:00:00+00:00", 105, 107, 98, 106),
        candle("2026-01-02T06:00:00+00:00", 106, 108, 100, 107),
        candle("2026-01-02T07:00:00+00:00", 109, 110, 107, 108),
        candle("2026-01-02T08:00:00+00:00", 112, 116, 111, 115),
    ]
    return candles + (extra or [])


def bearish_order_block_fixture(extra: list[dict] | None = None) -> list[dict]:
    candles = [
        candle("2026-01-02T00:00:00+00:00", 116, 117, 115, 116),
        candle("2026-01-02T01:00:00+00:00", 116, 116, 114, 115),
        candle("2026-01-02T02:00:00+00:00", 115, 115, 113, 114),
        candle("2026-01-02T03:00:00+00:00", 114, 114, 106, 112),
        candle("2026-01-02T04:00:00+00:00", 112, 115, 109, 111),
        candle("2026-01-02T05:00:00+00:00", 111, 118, 110, 112),
        candle("2026-01-02T06:00:00+00:00", 112, 116, 111, 113),
        candle("2026-01-02T07:00:00+00:00", 113, 116, 112, 114),
        candle("2026-01-02T08:00:00+00:00", 109, 110, 104, 105),
    ]
    return candles + (extra or [])


def verify_files() -> bool:
    files = [
        "backend/strategy_engine/order_block_detector.py",
        "backend/strategy_engine/order_block_quality_scorer.py",
        "docs/phase-6-day-5-progress.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    return show("Order block detector, scorer, and docs files exist", not missing, ", ".join(missing))


def verify_models() -> bool:
    try:
        from backend.strategy_engine.strategy_models import OrderBlock, SMCStructureContext

        ob_fields = set(OrderBlock.model_fields)
        smc_fields = set(SMCStructureContext.model_fields)
        expected_ob = {
            "order_block_id",
            "symbol",
            "direction",
            "creation_time",
            "upper_bound",
            "lower_bound",
            "midpoint",
            "active",
            "fresh",
            "mitigated",
            "broken",
            "strength",
            "quality",
            "aligned_with_structure",
            "aligned_with_liquidity",
            "aligned_with_fvg",
            "warnings",
        }
        expected_smc = {
            "order_blocks",
            "latest_order_block",
            "bullish_order_block_detected",
            "bearish_order_block_detected",
            "active_order_block_detected",
            "order_block_direction",
            "order_block_quality",
            "order_block_confidence",
            "order_block_alignment_reason",
        }
        return show("OrderBlock model and SMC order block fields exist", expected_ob <= ob_fields and expected_smc <= smc_fields)
    except Exception as exc:
        return show("OrderBlock model and SMC order block fields exist", False, str(exc))


def verify_no_candle_placeholder() -> bool:
    try:
        from backend.strategy_engine.order_block_detector import OrderBlockDetector

        result = OrderBlockDetector().detect()
        passed = result["order_blocks"] == [] and result["latest_order_block"] is None and result["warnings"]
        return show("No-candle order block placeholder is safe", passed)
    except Exception as exc:
        return show("No-candle order block placeholder is safe", False, str(exc))


def verify_bullish_bearish_order_blocks() -> bool:
    try:
        from backend.strategy_engine.smc_structure_detector import SMCStructureDetector

        bullish = SMCStructureDetector().detect(candles=bullish_order_block_fixture())
        bearish = SMCStructureDetector().detect(candles=bearish_order_block_fixture())
        passed = (
            bullish.bullish_order_block_detected is True
            and bullish.latest_order_block is not None
            and bullish.latest_order_block.direction == "BULLISH"
            and bullish.latest_order_block.lower_bound == 107
            and bullish.latest_order_block.upper_bound == 110
            and bearish.bearish_order_block_detected is True
            and bearish.latest_order_block is not None
            and bearish.latest_order_block.direction == "BEARISH"
            and bearish.latest_order_block.lower_bound == 112
            and bearish.latest_order_block.upper_bound == 116
        )
        return show("Bullish and bearish order blocks are detected", passed)
    except Exception as exc:
        return show("Bullish and bearish order blocks are detected", False, str(exc))


def verify_mitigation_and_broken_logic() -> bool:
    try:
        from backend.strategy_engine.smc_structure_detector import SMCStructureDetector

        mitigated = SMCStructureDetector().detect(
            candles=bullish_order_block_fixture(
                [candle("2026-01-02T09:00:00+00:00", 115, 116, 106.5, 111)]
            )
        ).latest_order_block
        broken = SMCStructureDetector().detect(
            candles=bullish_order_block_fixture(
                [candle("2026-01-02T09:00:00+00:00", 115, 116, 106.5, 106)]
            )
        ).latest_order_block
        passed = (
            mitigated is not None
            and mitigated.mitigated is True
            and mitigated.broken is False
            and mitigated.fill_percentage == 100.0
            and broken is not None
            and broken.broken is True
            and broken.active is False
        )
        return show("Order block mitigation and broken logic work", passed)
    except Exception as exc:
        return show("Order block mitigation and broken logic work", False, str(exc))


def verify_quality_and_alignment() -> bool:
    try:
        from backend.strategy_engine.order_block_detector import OrderBlockDetector
        from backend.strategy_engine.strategy_models import FairValueGap, LiquiditySweepContext, SMCStructureContext

        fvg = FairValueGap(
            fvg_id="fixture-fvg",
            symbol="XAUUSD",
            direction="BULLISH",
            start_time="2026-01-02T06:00:00+00:00",
            end_time="2026-01-02T08:00:00+00:00",
            upper_bound=111,
            lower_bound=108,
            midpoint=109.5,
            size=3,
            active=True,
        )
        structure = SMCStructureContext(
            symbol="XAUUSD",
            bos_direction="BULLISH_BOS",
            fair_value_gaps=[fvg],
            latest_fvg=fvg,
        )
        liquidity = LiquiditySweepContext(symbol="XAUUSD", sweep_direction="SELL_SIDE_SWEEP")
        latest = OrderBlockDetector().detect(
            candles=bullish_order_block_fixture(),
            structure_context=structure,
            liquidity_context=liquidity,
        )["latest_order_block"]
        passed = (
            latest is not None
            and latest.aligned_with_fvg is True
            and latest.aligned_with_liquidity is True
            and latest.aligned_with_structure is True
            and latest.strength >= 50
            and latest.quality in {"MEDIUM", "HIGH"}
        )
        return show("Order block quality, FVG alignment, and liquidity alignment work", passed)
    except Exception as exc:
        return show("Order block quality, FVG alignment, and liquidity alignment work", False, str(exc))


def verify_routes_and_strategy() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        get_response = client.get("/strategy/order-block/xauusd")
        post_response = client.post("/strategy/order-block/xauusd/analyze", json={"candles": bullish_order_block_fixture()})
        analyze_response = client.post("/strategy/analyze/xauusd", json={"candles": bullish_order_block_fixture()})
        payload = post_response.json()
        signal_payload = analyze_response.json()
        passed = (
            get_response.status_code == 200
            and post_response.status_code == 200
            and analyze_response.status_code == 200
            and payload["latest_order_block"]["direction"] == "BULLISH"
            and payload["active_order_block_detected"] is True
            and signal_payload["execution_allowed"] is False
            and signal_payload["metadata"]["simulation_only"] is True
            and "smc_context" in signal_payload
        )
        return show("Order block API route and XAUUSD analysis route work", passed)
    except Exception as exc:
        return show("Order block API route and XAUUSD analysis route work", False, str(exc))


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
            "/strategy/order-block/xauusd",
            "/strategy/order-block/xauusd/analyze",
            "/strategy/signals",
            "/strategy/signals/{signal_id}",
            "/strategy/session-context",
        }
        all_route_paths = {route.path for route in app.routes}
        missing = sorted(REQUIRED_GET_ROUTES - registered_get_routes)
        missing += sorted(expected_phase6 - all_route_paths)
        missing_ws = sorted(REQUIRED_WEBSOCKET_ROUTES - registered_websockets)
        return show("Phase 6 Day 1-4 and Phase 5 routes are preserved", not missing and not missing_ws, ", ".join(missing + missing_ws))
    except Exception as exc:
        return show("Phase 6 Day 1-4 and Phase 5 routes are preserved", False, str(exc))


def main() -> int:
    print("Phase 6 Day 5 Institutional Order Block Verification")
    print("=" * 64)
    checks = [
        verify_files(),
        verify_models(),
        verify_no_candle_placeholder(),
        verify_bullish_bearish_order_blocks(),
        verify_mitigation_and_broken_logic(),
        verify_quality_and_alignment(),
        verify_routes_and_strategy(),
        verify_order_send_isolated(),
        verify_preserved_routes(),
    ]
    print("=" * 64)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
