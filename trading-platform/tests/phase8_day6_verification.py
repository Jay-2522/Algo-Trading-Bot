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
    time = datetime(2026, 5, 30, hour % 24, 0, tzinfo=timezone.utc)
    return {
        "time": time.isoformat().replace("+00:00", "Z"),
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
    }


def high_session():
    from backend.strategy_engine.strategy_models import MarketSessionContext

    return MarketSessionContext(
        current_session="LONDON",
        is_london_session=True,
        is_new_york_session=False,
        is_asian_session=False,
        session_quality="HIGH",
    )


def trending_candles():
    return [
        candle(index, 1.0800 + index * 0.00035, 1.0807 + index * 0.00035, 1.0798 + index * 0.00035, 1.0805 + index * 0.00035)
        for index in range(30)
    ]


def ranging_candles():
    closes = [1.0800, 1.0810, 1.0802, 1.0811, 1.0801, 1.0809, 1.0800, 1.0810, 1.0802, 1.0811] * 3
    return [
        candle(index, price, 1.0813, 1.0798, price + (0.0001 if index % 2 == 0 else -0.0001))
        for index, price in enumerate(closes)
    ]


def high_volatility_candles():
    candles = [
        candle(index, 1.0800 + index * 0.0001, 1.0805 + index * 0.0001, 1.0797 + index * 0.0001, 1.0802 + index * 0.0001)
        for index in range(20)
    ]
    candles.append(candle(21, 1.0820, 1.0895, 1.0755, 1.0885))
    return candles


def low_volatility_candles():
    return [
        candle(index, 1.0800 + index * 0.00001, 1.08004 + index * 0.00001, 1.07999 + index * 0.00001, 1.08002 + index * 0.00001)
        for index in range(30)
    ]


def verify_files_and_models() -> bool:
    files = [
        "backend/strategy_engine/eurusd_regime_engine.py",
        "docs/phase-8-day-6-progress.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    try:
        from backend.strategy_engine.strategy_models import EURUSDRegimeContext, EURUSDStrategySignal

        expected = {
            "symbol",
            "regime",
            "trend_strength",
            "volatility_score",
            "range_score",
            "atr_state",
            "ema_alignment",
            "session_alignment",
            "tradeability",
            "risk_mode",
            "confidence",
            "warnings",
            "timestamp",
        }
        model_ok = expected <= set(EURUSDRegimeContext.model_fields) and "regime_context" in EURUSDStrategySignal.model_fields
    except Exception:
        model_ok = False
    return show("EURUSD regime engine, docs, and model exist", not missing and model_ok, ", ".join(missing))


def verify_regime_engine() -> bool:
    try:
        from backend.strategy_engine.eurusd_regime_engine import EURUSDRegimeEngine

        engine = EURUSDRegimeEngine()
        empty = engine.detect()
        trending = engine.detect(candles=trending_candles(), session_context=high_session())
        ranging = engine.detect(candles=ranging_candles(), session_context=high_session())
        high_volatility = engine.detect(candles=high_volatility_candles(), session_context=high_session())
        low_volatility = engine.detect(candles=low_volatility_candles(), session_context=high_session())
        passed = (
            empty.regime == "UNCLEAR"
            and empty.tradeability == "AVOID"
            and empty.risk_mode == "NO_TRADE"
            and empty.confidence == 0.0
            and empty.warnings
            and trending.regime == "TRENDING"
            and trending.tradeability in {"HIGH", "MEDIUM"}
            and trending.risk_mode == "NORMAL"
            and ranging.regime == "RANGING"
            and high_volatility.regime == "HIGH_VOLATILITY"
            and high_volatility.risk_mode in {"REDUCED_RISK", "NO_TRADE"}
            and low_volatility.regime == "LOW_VOLATILITY"
            and low_volatility.tradeability in {"LOW", "AVOID"}
            and low_volatility.risk_mode in {"REDUCED_RISK", "NO_TRADE"}
        )
        return show("EURUSD no-candle, trending, ranging, high-vol, low-vol, tradeability, and risk mode work", passed)
    except Exception as exc:
        return show("EURUSD no-candle, trending, ranging, high-vol, low-vol, tradeability, and risk mode work", False, str(exc))


def verify_routes_and_strategy() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        placeholder = client.get("/strategy/eurusd/regime")
        analyzed = client.post("/strategy/eurusd/regime/analyze", json={"candles": trending_candles()})
        signal = client.post("/strategy/analyze/eurusd", json={"candles": high_volatility_candles()})
        payload = signal.json()
        passed = (
            placeholder.status_code == 200
            and placeholder.json()["symbol"] == "EURUSD"
            and placeholder.json()["regime"] == "UNCLEAR"
            and analyzed.status_code == 200
            and analyzed.json()["regime"] == "TRENDING"
            and signal.status_code == 200
            and payload["symbol"] == "EURUSD"
            and payload["action"] == "WAIT"
            and payload["execution_allowed"] is False
            and "regime_context" in payload
            and payload["regime_context"]["regime"] == "HIGH_VOLATILITY"
            and payload["metadata"]["phase"] in {"PHASE_8_DAY_6", "PHASE_8_DAY_7"}
            and payload["metadata"]["regime_engine_integrated"] is True
            and payload["metadata"]["simulation_only"] is True
            and payload["metadata"]["live_execution_enabled"] is False
        )
        return show("EURUSD regime routes and strategy integration work", passed)
    except Exception as exc:
        return show("EURUSD regime routes and strategy integration work", False, str(exc))


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
            "/strategy/eurusd/regime",
            "/strategy/confluence/xauusd",
            "/strategy/order-block/xauusd",
            "/strategy/regime/xauusd",
            "/news/phase7/status",
            "/news/command-center",
        }
        missing = sorted((REQUIRED_GET_ROUTES | expected) - registered_get_routes)
        missing_ws = sorted(REQUIRED_WEBSOCKET_ROUTES - registered_websockets)
        return show("Phase 8 Day 1-5, XAUUSD, and Phase 7 routes are preserved", not missing and not missing_ws, ", ".join(missing + missing_ws))
    except Exception as exc:
        return show("Phase 8 Day 1-5, XAUUSD, and Phase 7 routes are preserved", False, str(exc))


def main() -> int:
    print("Phase 8 Day 6 EURUSD Market Regime Verification")
    print("=" * 60)
    checks = [
        verify_files_and_models(),
        verify_regime_engine(),
        verify_routes_and_strategy(),
        verify_no_order_send_added(),
        verify_preserved_routes(),
    ]
    print("=" * 60)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
