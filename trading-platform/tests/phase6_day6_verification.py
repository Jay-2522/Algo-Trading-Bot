import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def candle(hour: int, open_: float, high: float, low: float, close: float) -> dict:
    return {
        "time": f"2026-01-02T{hour % 24:02d}:00:00+00:00",
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": 100,
    }


def london_session():
    from backend.strategy_engine.strategy_models import MarketSessionContext

    return MarketSessionContext(
        current_session="LONDON",
        is_london_session=True,
        is_new_york_session=False,
        is_asian_session=False,
        session_quality="HIGH",
    )


def trending_candles() -> list[dict]:
    return [
        candle(index, 2300 + index * 2, 2303 + index * 2, 2299 + index * 2, 2302 + index * 2)
        for index in range(30)
    ]


def ranging_candles() -> list[dict]:
    closes = [2300, 2303, 2301, 2304, 2300, 2302, 2299, 2303, 2301, 2304] * 3
    return [
        candle(index, price, 2306, 2298, price + (0.5 if index % 2 == 0 else -0.5))
        for index, price in enumerate(closes)
    ]


def high_volatility_candles() -> list[dict]:
    candles = [
        candle(index, 2300 + index * 0.5, 2302 + index * 0.5, 2298 + index * 0.5, 2301 + index * 0.5)
        for index in range(20)
    ]
    candles.append(candle(21, 2310, 2400, 2220, 2380))
    return candles


def low_volatility_candles() -> list[dict]:
    return [
        candle(index, 2300 + index * 0.03, 2300.08 + index * 0.03, 2299.98 + index * 0.03, 2300.02 + index * 0.03)
        for index in range(30)
    ]


def verify_files() -> bool:
    files = [
        "backend/strategy_engine/market_regime_detector.py",
        "backend/strategy_engine/regime_quality_scorer.py",
        "docs/phase-6-day-6-progress.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    return show("Market regime detector, scorer, and docs files exist", not missing, ", ".join(missing))


def verify_model() -> bool:
    try:
        from backend.strategy_engine.strategy_models import MarketRegimeContext, XAUUSDStrategySignal

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
        passed = expected <= set(MarketRegimeContext.model_fields) and "regime_context" in XAUUSDStrategySignal.model_fields
        return show("MarketRegimeContext model and signal field exist", passed)
    except Exception as exc:
        return show("MarketRegimeContext model and signal field exist", False, str(exc))


def verify_no_candle_placeholder() -> bool:
    try:
        from backend.strategy_engine.market_regime_detector import MarketRegimeDetector

        context = MarketRegimeDetector().detect()
        passed = (
            context.regime == "UNCLEAR"
            and context.confidence == 0.0
            and context.tradeability in {"LOW", "AVOID"}
            and context.risk_mode == "NO_TRADE"
            and context.warnings
        )
        return show("No-candle regime placeholder is safe", passed)
    except Exception as exc:
        return show("No-candle regime placeholder is safe", False, str(exc))


def verify_regime_detection() -> bool:
    try:
        from backend.strategy_engine.market_regime_detector import MarketRegimeDetector

        detector = MarketRegimeDetector()
        trending = detector.detect(candles=trending_candles(), session_context=london_session())
        ranging = detector.detect(candles=ranging_candles(), session_context=london_session())
        high_volatility = detector.detect(candles=high_volatility_candles(), session_context=london_session())
        low_volatility = detector.detect(candles=low_volatility_candles(), session_context=london_session())
        passed = (
            trending.regime == "TRENDING"
            and trending.tradeability in {"HIGH", "MEDIUM"}
            and ranging.regime == "RANGING"
            and high_volatility.regime == "HIGH_VOLATILITY"
            and high_volatility.risk_mode in {"REDUCED_RISK", "NO_TRADE"}
            and low_volatility.regime == "LOW_VOLATILITY"
            and low_volatility.tradeability in {"LOW", "AVOID"}
            and trending.risk_mode == "NORMAL"
        )
        return show("Trending, ranging, high-volatility, and low-volatility regimes are detected", passed)
    except Exception as exc:
        return show("Trending, ranging, high-volatility, and low-volatility regimes are detected", False, str(exc))


def verify_tradeability_scoring() -> bool:
    try:
        from backend.strategy_engine.market_regime_detector import MarketRegimeDetector

        trending = MarketRegimeDetector().detect(candles=trending_candles(), session_context=london_session())
        high_volatility = MarketRegimeDetector().detect(candles=high_volatility_candles(), session_context=london_session())
        passed = (
            trending.confidence >= 75
            and trending.tradeability == "HIGH"
            and trending.risk_mode == "NORMAL"
            and high_volatility.confidence < trending.confidence
            and high_volatility.risk_mode in {"REDUCED_RISK", "NO_TRADE"}
        )
        return show("Regime tradeability and risk mode are calculated", passed)
    except Exception as exc:
        return show("Regime tradeability and risk mode are calculated", False, str(exc))


def verify_routes_and_strategy() -> bool:
    try:
        from backend.main import app
        from backend.strategy_engine.xauusd_strategy_engine import XAUUSDStrategyEngine

        client = TestClient(app)
        get_response = client.get("/strategy/regime/xauusd")
        post_response = client.post("/strategy/regime/xauusd/analyze", json={"candles": trending_candles()})
        analyze_response = client.post("/strategy/analyze/xauusd", json={"candles": high_volatility_candles()})
        signal = XAUUSDStrategyEngine().analyze(candles=low_volatility_candles())
        regime_payload = post_response.json()
        signal_payload = analyze_response.json()
        passed = (
            get_response.status_code == 200
            and post_response.status_code == 200
            and analyze_response.status_code == 200
            and regime_payload["regime"] == "TRENDING"
            and "regime_context" in signal_payload
            and signal_payload["regime_context"]["regime"] == "HIGH_VOLATILITY"
            and signal_payload["execution_allowed"] is False
            and signal.execution_allowed is False
            and signal.regime_context.regime == "LOW_VOLATILITY"
            and signal.action == "WAIT"
        )
        return show("Regime API route and XAUUSD strategy integration work", passed)
    except Exception as exc:
        return show("Regime API route and XAUUSD strategy integration work", False, str(exc))


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
            "/strategy/regime/xauusd",
            "/strategy/regime/xauusd/analyze",
            "/strategy/signals",
            "/strategy/signals/{signal_id}",
            "/strategy/session-context",
        }
        all_route_paths = {route.path for route in app.routes}
        missing = sorted(REQUIRED_GET_ROUTES - registered_get_routes)
        missing += sorted(expected_phase6 - all_route_paths)
        missing_ws = sorted(REQUIRED_WEBSOCKET_ROUTES - registered_websockets)
        return show("Phase 6 Day 1-5 and Phase 5 routes are preserved", not missing and not missing_ws, ", ".join(missing + missing_ws))
    except Exception as exc:
        return show("Phase 6 Day 1-5 and Phase 5 routes are preserved", False, str(exc))


def main() -> int:
    print("Phase 6 Day 6 Market Regime Verification")
    print("=" * 52)
    checks = [
        verify_files(),
        verify_model(),
        verify_no_candle_placeholder(),
        verify_regime_detection(),
        verify_tradeability_scoring(),
        verify_routes_and_strategy(),
        verify_order_send_isolated(),
        verify_preserved_routes(),
    ]
    print("=" * 52)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
