import sys
from datetime import datetime, timedelta, timezone
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


def bullish_bos_fixture():
    return [
        candle(0, 1.0800, 1.0810, 1.0790, 1.0805),
        candle(1, 1.0805, 1.0830, 1.0800, 1.0820),
        candle(2, 1.0820, 1.0824, 1.0808, 1.0810),
        candle(3, 1.0810, 1.0820, 1.0798, 1.0802),
        candle(4, 1.0802, 1.0835, 1.0800, 1.0828),
        candle(5, 1.0828, 1.0850, 1.0820, 1.0840),
        candle(6, 1.0840, 1.0843, 1.0825, 1.0830),
        candle(8, 1.0830, 1.0860, 1.0828, 1.0854),
    ]


def bearish_bos_fixture():
    return [
        candle(0, 1.0880, 1.0890, 1.0870, 1.0885),
        candle(1, 1.0885, 1.0895, 1.0860, 1.0870),
        candle(2, 1.0870, 1.0880, 1.0864, 1.0874),
        candle(3, 1.0874, 1.0882, 1.0850, 1.0858),
        candle(4, 1.0858, 1.0870, 1.0855, 1.0863),
        candle(5, 1.0863, 1.0873, 1.0835, 1.0840),
        candle(6, 1.0840, 1.0858, 1.0840, 1.0850),
        candle(8, 1.0850, 1.0853, 1.0824, 1.0830),
    ]


def bullish_choch_fixture():
    return [
        candle(0, 1.0900, 1.0910, 1.0890, 1.0900),
        candle(1, 1.0900, 1.0915, 1.0880, 1.0890),
        candle(2, 1.0890, 1.0900, 1.0885, 1.0894),
        candle(3, 1.0894, 1.0905, 1.0860, 1.0870),
        candle(4, 1.0870, 1.0880, 1.0865, 1.0875),
        candle(5, 1.0875, 1.0890, 1.0850, 1.0860),
        candle(6, 1.0860, 1.0872, 1.0855, 1.0868),
        candle(8, 1.0868, 1.0898, 1.0865, 1.0895),
    ]


def bearish_choch_fixture():
    return [
        candle(0, 1.0800, 1.0810, 1.0802, 1.0806),
        candle(1, 1.0800, 1.0820, 1.0795, 1.0810),
        candle(2, 1.0810, 1.0815, 1.0808, 1.0812),
        candle(3, 1.0808, 1.0830, 1.0805, 1.0822),
        candle(4, 1.0822, 1.0825, 1.0820, 1.0821),
        candle(5, 1.0815, 1.0840, 1.0812, 1.0830),
        candle(6, 1.0830, 1.0835, 1.0820, 1.0825),
        candle(8, 1.0825, 1.0828, 1.0802, 1.0804),
    ]


def verify_files_and_model() -> bool:
    files = [
        "backend/strategy_engine/eurusd_structure_engine.py",
        "docs/phase-8-day-3-progress.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    try:
        from backend.strategy_engine.strategy_models import EURUSDStrategySignal, EURUSDStructureContext

        model_ok = (
            "bos_direction" in EURUSDStructureContext.model_fields
            and "choch_direction" in EURUSDStructureContext.model_fields
            and "post_sweep_confirmation" in EURUSDStructureContext.model_fields
            and "structure_context" in EURUSDStrategySignal.model_fields
        )
    except Exception:
        model_ok = False
    return show("EURUSD structure engine, docs, and model exist", not missing and model_ok, ", ".join(missing))


def verify_structure_engine() -> bool:
    try:
        from backend.strategy_engine.eurusd_structure_engine import EURUSDStructureEngine
        from backend.strategy_engine.strategy_models import EURUSDLiquidityContext

        engine = EURUSDStructureEngine()
        empty = engine.detect()
        bullish_bos = engine.detect(bullish_bos_fixture())
        bearish_bos = engine.detect(bearish_bos_fixture())
        bullish_choch = engine.detect(bullish_choch_fixture())
        bearish_choch = engine.detect(bearish_choch_fixture())
        sell_sweep_confirm = engine.detect(
            bullish_bos_fixture(),
            liquidity_context=EURUSDLiquidityContext(sweep_direction="SELL_SIDE_SWEEP"),
        )
        buy_sweep_confirm = engine.detect(
            bearish_bos_fixture(),
            liquidity_context=EURUSDLiquidityContext(sweep_direction="BUY_SIDE_SWEEP"),
        )
        passed = (
            engine.tolerance == 0.0002
            and empty.bos_direction == "NONE"
            and empty.choch_direction == "NONE"
            and empty.structure_bias == "NEUTRAL"
            and empty.warnings
            and bullish_bos.bos_direction == "BULLISH_BOS"
            and bullish_bos.structure_bias == "BULLISH"
            and bearish_bos.bos_direction == "BEARISH_BOS"
            and bearish_bos.structure_bias == "BEARISH"
            and bullish_choch.choch_direction == "BULLISH_CHOCH"
            and bearish_choch.choch_direction == "BEARISH_CHOCH"
            and sell_sweep_confirm.post_sweep_confirmation is True
            and buy_sweep_confirm.post_sweep_confirmation is True
            and bullish_bos.structure_strength > 0
            and bullish_bos.confidence > 0
            and bullish_bos.structure_quality in {"LOW", "MEDIUM", "HIGH"}
        )
        return show("EURUSD BOS, CHOCH, post-sweep confirmation, scoring, and tolerance work", passed)
    except Exception as exc:
        return show("EURUSD BOS, CHOCH, post-sweep confirmation, scoring, and tolerance work", False, str(exc))


def verify_routes_and_strategy() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        placeholder = client.get("/strategy/eurusd/structure")
        analyzed = client.post("/strategy/eurusd/structure/analyze", json={"candles": bullish_bos_fixture()})
        signal = client.post("/strategy/analyze/eurusd", json={"candles": bullish_bos_fixture()})
        payload = signal.json()
        passed = (
            placeholder.status_code == 200
            and placeholder.json()["symbol"] == "EURUSD"
            and placeholder.json()["bos_direction"] == "NONE"
            and analyzed.status_code == 200
            and analyzed.json()["bos_direction"] == "BULLISH_BOS"
            and signal.status_code == 200
            and payload["symbol"] == "EURUSD"
            and payload["action"] == "WAIT"
            and payload["execution_allowed"] is False
            and "structure_context" in payload
            and payload["structure_context"]["bos_direction"] == "BULLISH_BOS"
            and payload["metadata"]["phase"] in {"PHASE_8_DAY_3", "PHASE_8_DAY_4"}
            and payload["metadata"]["structure_engine_integrated"] is True
            and payload["metadata"]["simulation_only"] is True
            and payload["metadata"]["live_execution_enabled"] is False
        )
        return show("EURUSD structure routes and strategy integration work", passed)
    except Exception as exc:
        return show("EURUSD structure routes and strategy integration work", False, str(exc))


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
            "/strategy/confluence/xauusd",
            "/strategy/liquidity/xauusd",
            "/news/phase7/status",
            "/news/command-center",
        }
        missing = sorted((REQUIRED_GET_ROUTES | expected) - registered_get_routes)
        missing_ws = sorted(REQUIRED_WEBSOCKET_ROUTES - registered_websockets)
        return show("Phase 8 Day 1-2, XAUUSD, and Phase 7 routes are preserved", not missing and not missing_ws, ", ".join(missing + missing_ws))
    except Exception as exc:
        return show("Phase 8 Day 1-2, XAUUSD, and Phase 7 routes are preserved", False, str(exc))


def main() -> int:
    print("Phase 8 Day 3 EURUSD BOS / CHOCH Verification")
    print("=" * 58)
    checks = [
        verify_files_and_model(),
        verify_structure_engine(),
        verify_routes_and_strategy(),
        verify_no_order_send_added(),
        verify_preserved_routes(),
    ]
    print("=" * 58)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
