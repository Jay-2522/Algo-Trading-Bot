import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def verify_files() -> bool:
    files = [
        "backend/strategy_engine/__init__.py",
        "backend/strategy_engine/strategy_models.py",
        "backend/strategy_engine/market_session_service.py",
        "backend/strategy_engine/indicator_context_builder.py",
        "backend/strategy_engine/swing_point_detector.py",
        "backend/strategy_engine/bos_choch_detector.py",
        "backend/strategy_engine/fvg_detector.py",
        "backend/strategy_engine/fvg_quality_scorer.py",
        "backend/strategy_engine/liquidity_level_builder.py",
        "backend/strategy_engine/liquidity_sweep_detector.py",
        "backend/strategy_engine/smc_structure_detector.py",
        "backend/strategy_engine/xauusd_strategy_engine.py",
        "backend/strategy_engine/structure_strength_scorer.py",
        "backend/strategy_engine/sweep_strength_scorer.py",
        "backend/strategy_engine/strategy_signal_store.py",
        "backend/strategy_engine/strategy_service.py",
        "backend/api/strategy_routes.py",
        "docs/phase-6-day-1-progress.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    return show("Strategy engine package, router, and docs files exist", not missing, ", ".join(missing))


def verify_routes_registered() -> bool:
    try:
        from backend.main import app

        routes = {route.path for route in app.routes}
        expected = {
            "/strategy/status",
            "/strategy/analyze/xauusd",
            "/strategy/signals",
            "/strategy/signals/{signal_id}",
            "/strategy/session-context",
            "/strategy/session",
        }
        return show("Phase 6 strategy routes registered", expected <= routes)
    except Exception as exc:
        return show("Phase 6 strategy routes registered", False, str(exc))


def verify_session_service() -> bool:
    try:
        from backend.strategy_engine.market_session_service import MarketSessionService

        context = MarketSessionService().get_session_context(datetime(2026, 1, 1, 13, 0, tzinfo=timezone.utc))
        passed = (
            context.current_session == "OVERLAP"
            and context.is_london_session is True
            and context.is_new_york_session is True
            and context.session_quality == "HIGH"
        )
        return show("Market session service classifies UTC overlap window", passed)
    except Exception as exc:
        return show("Market session service classifies UTC overlap window", False, str(exc))


def verify_safe_context_builders() -> bool:
    try:
        from backend.strategy_engine.indicator_context_builder import IndicatorContextBuilder
        from backend.strategy_engine.liquidity_sweep_detector import LiquiditySweepDetector
        from backend.strategy_engine.smc_structure_detector import SMCStructureDetector

        indicator = IndicatorContextBuilder().build_context()
        liquidity = LiquiditySweepDetector().detect()
        smc = SMCStructureDetector().detect()
        passed = (
            indicator.symbol == "XAUUSD"
            and indicator.trend_bias == "NEUTRAL"
            and indicator.warnings
            and liquidity.sweep_direction == "NONE"
            and liquidity.confidence == 0.0
            and liquidity.sweep_quality == "NONE"
            and liquidity.warnings
            and smc.structure_bias == "NEUTRAL"
            and smc.confidence == 0.0
            and smc.bos_direction == "NONE"
            and smc.choch_direction == "NONE"
            and smc.fair_value_gaps == []
            and smc.fvg_quality == "NONE"
            and smc.warnings
        )
        return show("Indicator, liquidity, and SMC builders return safe placeholder contexts", passed)
    except Exception as exc:
        return show("Indicator, liquidity, and SMC builders return safe placeholder contexts", False, str(exc))


def verify_engine_signal() -> bool:
    try:
        from backend.strategy_engine.xauusd_strategy_engine import XAUUSDStrategyEngine

        signal = XAUUSDStrategyEngine().analyze()
        passed = (
            signal.symbol == "XAUUSD"
            and signal.action in {"BUY", "SELL", "WAIT"}
            and signal.action == "WAIT"
            and signal.execution_allowed is False
            and signal.indicator_context.symbol == "XAUUSD"
            and signal.liquidity_context.sweep_direction == "NONE"
            and signal.smc_context.structure_bias == "NEUTRAL"
        )
        return show("XAUUSD strategy engine returns risk-safe analysis signal", passed)
    except Exception as exc:
        return show("XAUUSD strategy engine returns risk-safe analysis signal", False, str(exc))


def verify_service_and_endpoints() -> bool:
    try:
        from backend.main import app
        from backend.strategy_engine.strategy_service import StrategyService

        service = StrategyService()
        status = service.get_status()
        signal = service.analyze_xauusd()
        listed = service.list_signals()
        fetched = service.get_signal(signal.signal_id)
        service.close()

        client = TestClient(app)
        status_response = client.get("/strategy/status")
        analyze_response = client.post("/strategy/analyze/xauusd", json={})
        signals_response = client.get("/strategy/signals")
        session_response = client.get("/strategy/session-context")
        payload = analyze_response.json()

        passed = (
            status["status"] == "OPERATIONAL"
            and status["execution_allowed"] is False
            and status["simulation_only"] is True
            and status["live_execution_enabled"] is False
            and status["broker_execution_enabled"] is False
            and signal.execution_allowed is False
            and listed
            and fetched is not None
            and status_response.status_code == 200
            and analyze_response.status_code == 200
            and signals_response.status_code == 200
            and session_response.status_code == 200
            and payload["symbol"] == "XAUUSD"
            and payload["action"] in {"BUY", "SELL", "WAIT"}
            and payload["action"] == "WAIT"
            and payload["execution_allowed"] is False
            and "session_context" in payload
            and "indicator_context" in payload
            and "liquidity_context" in payload
            and "smc_context" in payload
            and "reason" in payload
        )
        return show("Strategy service and API endpoints return analysis-only payloads", passed)
    except Exception as exc:
        return show("Strategy service and API endpoints return analysis-only payloads", False, str(exc))


def verify_order_send_isolated() -> bool:
    token = "mt5." + "order_send"
    matches = []
    for path in (PROJECT_ROOT / "backend").rglob("*.py"):
        if path.is_file() and token in path.read_text(encoding="utf-8", errors="ignore"):
            matches.append(path.relative_to(PROJECT_ROOT).as_posix())
    passed = matches == ["backend/demo_execution/mt5_demo_executor.py"]
    return show("MT5 order submission remains isolated to guarded demo executor", passed, ", ".join(matches))


def verify_no_execution_call_added() -> bool:
    forbidden = ["order_send", "execute_demo", "execute_trade", "place_order"]
    files = [
        PROJECT_ROOT / "backend/strategy_engine/strategy_models.py",
        PROJECT_ROOT / "backend/strategy_engine/market_session_service.py",
        PROJECT_ROOT / "backend/strategy_engine/indicator_context_builder.py",
        PROJECT_ROOT / "backend/strategy_engine/swing_point_detector.py",
        PROJECT_ROOT / "backend/strategy_engine/bos_choch_detector.py",
        PROJECT_ROOT / "backend/strategy_engine/fvg_detector.py",
        PROJECT_ROOT / "backend/strategy_engine/fvg_quality_scorer.py",
        PROJECT_ROOT / "backend/strategy_engine/liquidity_level_builder.py",
        PROJECT_ROOT / "backend/strategy_engine/liquidity_sweep_detector.py",
        PROJECT_ROOT / "backend/strategy_engine/smc_structure_detector.py",
        PROJECT_ROOT / "backend/strategy_engine/xauusd_strategy_engine.py",
        PROJECT_ROOT / "backend/strategy_engine/structure_strength_scorer.py",
        PROJECT_ROOT / "backend/strategy_engine/sweep_strength_scorer.py",
        PROJECT_ROOT / "backend/strategy_engine/strategy_signal_store.py",
        PROJECT_ROOT / "backend/api/strategy_routes.py",
    ]
    offenders = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in forbidden:
            if token in text:
                offenders.append(f"{path.relative_to(PROJECT_ROOT).as_posix()}:{token}")
    return show("Strategy engine contains no execution call path", not offenders, ", ".join(offenders))


def verify_platform_safety_and_routes() -> bool:
    try:
        from backend.main import app
        from backend.system_health.module_registry import get_module_registry
        from tests.regression_routes_verification import REQUIRED_GET_ROUTES, REQUIRED_WEBSOCKET_ROUTES

        registry = get_module_registry()
        strategy_module = next(module for module in registry if module["name"] == "xauusd_strategy_engine")
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
        missing = sorted(REQUIRED_GET_ROUTES - registered_get_routes)
        missing_ws = sorted(REQUIRED_WEBSOCKET_ROUTES - registered_websockets)
        passed = (
            strategy_module["simulation_only"] is True
            and strategy_module["live_execution_enabled"] is False
            and "/execution-dashboard/status" in registered_get_routes
            and not missing
            and not missing_ws
        )
        return show("Simulation safety flags and Phase 5 routes are preserved", passed, ", ".join(missing + missing_ws))
    except Exception as exc:
        return show("Simulation safety flags and Phase 5 routes are preserved", False, str(exc))


def main() -> int:
    print("Phase 6 Day 1 XAUUSD Strategy Engine Verification")
    print("=" * 58)
    checks = [
        verify_files(),
        verify_routes_registered(),
        verify_session_service(),
        verify_safe_context_builders(),
        verify_engine_signal(),
        verify_service_and_endpoints(),
        verify_order_send_isolated(),
        verify_no_execution_call_added(),
        verify_platform_safety_and_routes(),
    ]
    print("=" * 58)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
