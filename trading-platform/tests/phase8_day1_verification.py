import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def verify_files_and_model() -> bool:
    files = [
        "backend/strategy_engine/eurusd_strategy_engine.py",
        "backend/strategy_engine/eurusd_strategy_service.py",
        "docs/phase-8-day-1-progress.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    try:
        from backend.strategy_engine.strategy_models import EURUSDStrategySignal

        model_ok = (
            "signal_id" in EURUSDStrategySignal.model_fields
            and "session_context" in EURUSDStrategySignal.model_fields
            and "indicator_context" in EURUSDStrategySignal.model_fields
            and "execution_allowed" in EURUSDStrategySignal.model_fields
        )
    except Exception:
        model_ok = False
    return show("EURUSD engine, service, docs, and model exist", not missing and model_ok, ", ".join(missing))


def verify_engine_foundation() -> bool:
    try:
        from backend.strategy_engine.eurusd_strategy_engine import EURUSDStrategyEngine

        engine = EURUSDStrategyEngine()
        signal = engine.analyze()
        session = engine.build_session_context()
        indicators = engine.build_indicator_context()
        passed = (
            signal.symbol == "EURUSD"
            and signal.action == "WAIT"
            and signal.execution_allowed is False
            and signal.confidence <= 20
            and signal.metadata["instrument"] == "EURUSD"
            and signal.metadata["phase"] in {"PHASE_8_DAY_1", "PHASE_8_DAY_2", "PHASE_8_DAY_3", "PHASE_8_DAY_4", "PHASE_8_DAY_5", "PHASE_8_DAY_6", "PHASE_8_DAY_7"}
            and signal.metadata["simulation_only"] is True
            and signal.metadata["live_execution_enabled"] is False
            and session.current_session in {"ASIAN", "LONDON", "NEW_YORK", "OVERLAP", "OFF_SESSION"}
            and session.session_quality in {"HIGH", "MEDIUM", "LOW"}
            and indicators.symbol == "EURUSD"
            and indicators.timeframe == "H1"
            and indicators.trend_bias in {"BULLISH", "BEARISH", "NEUTRAL"}
        )
        return show("EURUSD engine, session context, indicator context, and safe WAIT signal work", passed)
    except Exception as exc:
        return show("EURUSD engine, session context, indicator context, and safe WAIT signal work", False, str(exc))


def verify_routes_and_persistence_compatibility() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        analyze = client.get("/strategy/analyze/eurusd")
        session = client.get("/strategy/eurusd/session-context")
        indicators = client.get("/strategy/eurusd/indicator-context")
        signals = client.get("/strategy/signals")
        payload = analyze.json()
        passed = (
            analyze.status_code == 200
            and payload["symbol"] == "EURUSD"
            and payload["action"] == "WAIT"
            and payload["execution_allowed"] is False
            and payload["metadata"]["instrument"] == "EURUSD"
            and payload["metadata"]["phase"] in {"PHASE_8_DAY_1", "PHASE_8_DAY_2", "PHASE_8_DAY_3", "PHASE_8_DAY_4", "PHASE_8_DAY_5", "PHASE_8_DAY_6", "PHASE_8_DAY_7"}
            and payload["metadata"]["simulation_only"] is True
            and payload["metadata"]["live_execution_enabled"] is False
            and session.status_code == 200
            and "current_session" in session.json()
            and "session_quality" in session.json()
            and indicators.status_code == 200
            and indicators.json()["symbol"] == "EURUSD"
            and "indicator_quality" in indicators.json()
            and signals.status_code == 200
            and any(signal["symbol"] == "EURUSD" for signal in signals.json())
        )
        return show("EURUSD routes and signal persistence compatibility work", passed)
    except Exception as exc:
        return show("EURUSD routes and signal persistence compatibility work", False, str(exc))


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
            "/strategy/confluence/xauusd",
            "/strategy/structure/xauusd",
            "/news/phase7/status",
            "/news/command-center",
            "/news/unified-risk/xauusd",
        }
        missing = sorted((REQUIRED_GET_ROUTES | expected) - registered_get_routes)
        missing_ws = sorted(REQUIRED_WEBSOCKET_ROUTES - registered_websockets)
        return show("Phase 7 and Phase 6 routes are preserved", not missing and not missing_ws, ", ".join(missing + missing_ws))
    except Exception as exc:
        return show("Phase 7 and Phase 6 routes are preserved", False, str(exc))


def main() -> int:
    print("Phase 8 Day 1 EURUSD Strategy Foundation Verification")
    print("=" * 62)
    checks = [
        verify_files_and_model(),
        verify_engine_foundation(),
        verify_routes_and_persistence_compatibility(),
        verify_no_order_send_added(),
        verify_preserved_routes(),
    ]
    print("=" * 62)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
