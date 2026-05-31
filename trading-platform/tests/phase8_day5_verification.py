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


def bullish_ob_fixture():
    return [
        candle(7, 1.0808, 1.0810, 1.0800, 1.0802),
        candle(8, 1.0802, 1.0830, 1.0801, 1.0828),
        candle(9, 1.0828, 1.0832, 1.0813, 1.0829),
    ]


def bearish_ob_fixture():
    return [
        candle(7, 1.0850, 1.0860, 1.0848, 1.0858),
        candle(8, 1.0858, 1.0859, 1.0830, 1.0832),
        candle(9, 1.0832, 1.0845, 1.0828, 1.0830),
    ]


def tiny_origin_fixture():
    return [
        candle(7, 1.08004, 1.08005, 1.08000, 1.08001),
        candle(8, 1.08001, 1.0825, 1.0800, 1.0822),
        candle(9, 1.0822, 1.0826, 1.0804, 1.0824),
    ]


def mitigated_bullish_fixture():
    return bullish_ob_fixture() + [candle(10, 1.0829, 1.0830, 1.0805, 1.0812)]


def broken_bullish_fixture():
    return bullish_ob_fixture() + [candle(10, 1.0829, 1.0830, 1.0795, 1.0797)]


def broken_bearish_fixture():
    return bearish_ob_fixture() + [candle(10, 1.0830, 1.0865, 1.0829, 1.0863)]


def verify_files_and_models() -> bool:
    files = [
        "backend/strategy_engine/eurusd_order_block_engine.py",
        "docs/phase-8-day-5-progress.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    try:
        from backend.strategy_engine.strategy_models import (
            EURUSDOrderBlock,
            EURUSDOrderBlockContext,
            EURUSDStrategySignal,
        )

        model_ok = (
            "fill_percentage" in EURUSDOrderBlock.model_fields
            and "aligned_with_fvg" in EURUSDOrderBlock.model_fields
            and "latest_order_block" in EURUSDOrderBlockContext.model_fields
            and "order_block_context" in EURUSDStrategySignal.model_fields
        )
    except Exception:
        model_ok = False
    return show("EURUSD order block engine, docs, and models exist", not missing and model_ok, ", ".join(missing))


def verify_order_block_engine() -> bool:
    try:
        from backend.strategy_engine.eurusd_order_block_engine import EURUSDOrderBlockEngine

        engine = EURUSDOrderBlockEngine()
        empty = engine.detect()
        bullish = engine.detect(bullish_ob_fixture(), structure_context={"bos_direction": "BULLISH_BOS"})
        bearish = engine.detect(bearish_ob_fixture(), structure_context={"bos_direction": "BEARISH_BOS"})
        tiny = engine.detect(tiny_origin_fixture(), structure_context={"bos_direction": "BULLISH_BOS"})
        mitigated = engine.detect(mitigated_bullish_fixture(), structure_context={"bos_direction": "BULLISH_BOS"})
        broken_bullish = engine.detect(broken_bullish_fixture(), structure_context={"bos_direction": "BULLISH_BOS"})
        broken_bearish = engine.detect(broken_bearish_fixture(), structure_context={"bos_direction": "BEARISH_BOS"})
        fvg_aligned = engine.detect(
            bullish_ob_fixture(),
            fvg_context={"latest_fvg": {"direction": "BULLISH"}, "fair_value_gaps": []},
        )
        liquidity_aligned = engine.detect(
            bullish_ob_fixture(),
            structure_context={"bos_direction": "BULLISH_BOS"},
            liquidity_context={"sweep_direction": "SELL_SIDE_SWEEP"},
        )
        passed = (
            engine.tolerance == 0.0002
            and engine.min_candle_range == 0.0001
            and empty.order_blocks == []
            and empty.warnings
            and bullish.bullish_order_block_detected is True
            and bullish.latest_order_block is not None
            and bullish.latest_order_block.direction == "BULLISH"
            and bullish.latest_order_block.upper_bound == 1.081
            and bearish.bearish_order_block_detected is True
            and bearish.latest_order_block is not None
            and bearish.latest_order_block.direction == "BEARISH"
            and bearish.latest_order_block.lower_bound == 1.0848
            and tiny.order_blocks == []
            and mitigated.latest_order_block is not None
            and mitigated.latest_order_block.mitigated is True
            and mitigated.latest_order_block.fresh is False
            and broken_bullish.latest_order_block is not None
            and broken_bullish.latest_order_block.broken is True
            and broken_bullish.latest_order_block.active is False
            and broken_bearish.latest_order_block is not None
            and broken_bearish.latest_order_block.broken is True
            and fvg_aligned.latest_order_block is not None
            and fvg_aligned.latest_order_block.aligned_with_fvg is True
            and liquidity_aligned.latest_order_block is not None
            and liquidity_aligned.latest_order_block.aligned_with_liquidity is True
            and liquidity_aligned.latest_order_block.quality in {"MEDIUM", "HIGH"}
        )
        return show("EURUSD order block detection, filtering, mitigation, broken logic, and alignment work", passed)
    except Exception as exc:
        return show("EURUSD order block detection, filtering, mitigation, broken logic, and alignment work", False, str(exc))


def verify_routes_and_strategy() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        placeholder = client.get("/strategy/eurusd/order-block")
        analyzed = client.post("/strategy/eurusd/order-block/analyze", json={"candles": bullish_ob_fixture()})
        signal = client.post("/strategy/analyze/eurusd", json={"candles": bullish_ob_fixture()})
        payload = signal.json()
        passed = (
            placeholder.status_code == 200
            and placeholder.json()["symbol"] == "EURUSD"
            and placeholder.json()["active_order_block_detected"] is False
            and analyzed.status_code == 200
            and analyzed.json()["order_block_direction"] == "BULLISH"
            and signal.status_code == 200
            and payload["symbol"] == "EURUSD"
            and payload["action"] == "WAIT"
            and payload["execution_allowed"] is False
            and "order_block_context" in payload
            and payload["order_block_context"]["order_block_direction"] == "BULLISH"
            and payload["metadata"]["phase"] == "PHASE_8_DAY_5"
            and payload["metadata"]["order_block_engine_integrated"] is True
            and payload["metadata"]["simulation_only"] is True
            and payload["metadata"]["live_execution_enabled"] is False
        )
        return show("EURUSD order block routes and strategy integration work", passed)
    except Exception as exc:
        return show("EURUSD order block routes and strategy integration work", False, str(exc))


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
            "/strategy/eurusd/order-block",
            "/strategy/confluence/xauusd",
            "/strategy/order-block/xauusd",
            "/news/phase7/status",
            "/news/command-center",
        }
        missing = sorted((REQUIRED_GET_ROUTES | expected) - registered_get_routes)
        missing_ws = sorted(REQUIRED_WEBSOCKET_ROUTES - registered_websockets)
        return show("Phase 8 Day 1-4, XAUUSD, and Phase 7 routes are preserved", not missing and not missing_ws, ", ".join(missing + missing_ws))
    except Exception as exc:
        return show("Phase 8 Day 1-4, XAUUSD, and Phase 7 routes are preserved", False, str(exc))


def main() -> int:
    print("Phase 8 Day 5 EURUSD Order Block Verification")
    print("=" * 59)
    checks = [
        verify_files_and_models(),
        verify_order_block_engine(),
        verify_routes_and_strategy(),
        verify_no_order_send_added(),
        verify_preserved_routes(),
    ]
    print("=" * 59)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
