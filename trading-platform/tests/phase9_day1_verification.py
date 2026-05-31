import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def signal(**overrides):
    payload = {
        "signal_id": "manual-signal-001",
        "symbol": "EURUSD",
        "action": "BUY",
        "confidence": 85.0,
        "execution_allowed": False,
        "trade_quality": "A",
        "news_context": {"high_impact_event_active": False, "trade_action": "ALLOW", "risk_level": "LOW"},
        "regime_context": {"risk_mode": "NORMAL"},
        "metadata": {
            "phase": "PHASE_8_DAY_7",
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        },
        "reason": "Manual bridge verification signal.",
    }
    payload.update(overrides)
    return payload


def verify_files() -> bool:
    files = [
        "backend/strategy_execution_bridge/__init__.py",
        "backend/strategy_execution_bridge/bridge_models.py",
        "backend/strategy_execution_bridge/signal_eligibility_validator.py",
        "backend/strategy_execution_bridge/strategy_to_intent_mapper.py",
        "backend/strategy_execution_bridge/bridge_decision_store.py",
        "backend/strategy_execution_bridge/strategy_execution_bridge_service.py",
        "backend/api/strategy_execution_bridge_routes.py",
        "docs/phase-9-day-1-progress.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    return show("Strategy execution bridge package, router, and docs exist", not missing, ", ".join(missing))


def verify_models_and_validator() -> bool:
    try:
        from backend.strategy_execution_bridge.bridge_models import StrategyBridgeDecision, StrategyExecutionIntent
        from backend.strategy_execution_bridge.signal_eligibility_validator import SignalEligibilityValidator

        validator = SignalEligibilityValidator()
        wait = validator.validate(signal(action="WAIT", confidence=10, trade_quality="NO_TRADE"))
        low = validator.validate(signal(confidence=50, execution_allowed=True, trade_quality="C"))
        disabled = validator.validate(signal(execution_allowed=False))
        news = validator.validate(signal(execution_allowed=True, news_context={"high_impact_event_active": True, "trade_action": "BLOCK"}))
        regime = validator.validate(signal(execution_allowed=True, regime_context={"risk_mode": "NO_TRADE"}))
        passed = (
            "bridge_status" in StrategyBridgeDecision.model_fields
            and "source_signal_id" in StrategyExecutionIntent.model_fields
            and wait[1] == "REJECTED_WAIT_SIGNAL"
            and low[1] == "REJECTED_LOW_CONFIDENCE"
            and disabled[1] == "REJECTED_EXECUTION_NOT_ALLOWED"
            and news[1] == "REJECTED_NEWS_RISK"
            and regime[1] == "REJECTED_REGIME"
        )
        return show("Bridge models and eligibility rejection rules work", passed)
    except Exception as exc:
        return show("Bridge models and eligibility rejection rules work", False, str(exc))


def verify_mapper_and_store() -> bool:
    try:
        from backend.strategy_execution_bridge.bridge_decision_store import BridgeDecisionStore
        from backend.strategy_execution_bridge.bridge_models import StrategyBridgeDecision
        from backend.strategy_execution_bridge.strategy_to_intent_mapper import StrategyToIntentMapper

        intent = StrategyToIntentMapper().map_signal_to_intent(signal(execution_allowed=True))
        store = BridgeDecisionStore()
        decision = store.store_decision(
            StrategyBridgeDecision(
                signal_id="store-test",
                symbol="EURUSD",
                action="BUY",
                confidence=85,
                eligible=False,
                bridge_status="REJECTED_EXECUTION_NOT_ALLOWED",
            )
        )
        passed = (
            intent.symbol == "EURUSD"
            and intent.action == "BUY"
            and intent.suggested_lot == 0.01
            and intent.total_lot == 0.01
            and intent.allocation_mode == "EQUAL"
            and intent.simulation_only is True
            and intent.demo_execution is True
            and intent.live_execution_enabled is False
            and store.get_decision(decision.decision_id) is not None
            and decision in store.list_decisions(100)
        )
        return show("Signal-to-intent mapper and decision store work", passed)
    except Exception as exc:
        return show("Signal-to-intent mapper and decision store work", False, str(exc))


def verify_service_and_routes() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        status = client.get("/strategy-execution-bridge/status")
        wait = client.post("/strategy-execution-bridge/evaluate-signal", json=signal(action="WAIT", confidence=10, trade_quality="NO_TRADE"))
        low = client.post("/strategy-execution-bridge/evaluate-signal", json=signal(confidence=50, trade_quality="C"))
        disabled = client.post("/strategy-execution-bridge/evaluate-signal", json=signal(symbol="EURUSD", confidence=85, execution_allowed=False))
        xauusd = client.post("/strategy-execution-bridge/xauusd/latest")
        eurusd = client.post("/strategy-execution-bridge/eurusd/latest")
        decisions = client.get("/strategy-execution-bridge/decisions")
        decision_id = disabled.json()["decision_id"]
        one_decision = client.get(f"/strategy-execution-bridge/decisions/{decision_id}")
        passed = (
            status.status_code == 200
            and status.json()["simulation_only"] is True
            and status.json()["demo_execution"] is True
            and status.json()["live_execution_enabled"] is False
            and status.json()["broker_execution_enabled"] is False
            and wait.status_code == 200
            and wait.json()["bridge_status"] == "REJECTED_WAIT_SIGNAL"
            and wait.json()["eligible"] is False
            and wait.json()["queue_preview_id"] is None
            and low.json()["bridge_status"] == "REJECTED_LOW_CONFIDENCE"
            and low.json()["queue_preview_id"] is None
            and disabled.json()["bridge_status"] == "REJECTED_EXECUTION_NOT_ALLOWED"
            and disabled.json()["queue_preview_id"] is None
            and xauusd.status_code == 200
            and xauusd.json()["eligible"] is False
            and xauusd.json()["queue_preview_id"] is None
            and eurusd.status_code == 200
            and eurusd.json()["eligible"] is False
            and eurusd.json()["queue_preview_id"] is None
            and decisions.status_code == 200
            and one_decision.status_code == 200
            and one_decision.json()["decision_id"] == decision_id
        )
        return show("Bridge service status and API routes reject safely", passed)
    except Exception as exc:
        return show("Bridge service status and API routes reject safely", False, str(exc))


def verify_routes_preserved() -> bool:
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
            "/strategy/eurusd/confluence",
            "/strategy/confluence/xauusd",
            "/news/phase7/status",
            "/execution-queue/status",
            "/strategy-execution-bridge/status",
            "/strategy-execution-bridge/decisions",
        }
        missing = sorted((REQUIRED_GET_ROUTES | expected) - registered_get_routes)
        missing_ws = sorted(REQUIRED_WEBSOCKET_ROUTES - registered_websockets)
        return show("Phase 8, Phase 7, and execution queue routes are preserved", not missing and not missing_ws, ", ".join(missing + missing_ws))
    except Exception as exc:
        return show("Phase 8, Phase 7, and execution queue routes are preserved", False, str(exc))


def verify_no_order_send_added() -> bool:
    token = "mt5." + "order_send"
    matches = []
    for path in (PROJECT_ROOT / "backend").rglob("*.py"):
        if path.is_file() and token in path.read_text(encoding="utf-8", errors="ignore"):
            matches.append(path.relative_to(PROJECT_ROOT).as_posix())
    passed = matches == ["backend/demo_execution/mt5_demo_executor.py"]
    return show("MT5 order submission remains isolated to guarded demo executor", passed, ", ".join(matches))


def main() -> int:
    print("Phase 9 Day 1 Strategy Execution Bridge Verification")
    print("=" * 63)
    checks = [
        verify_files(),
        verify_models_and_validator(),
        verify_mapper_and_store(),
        verify_service_and_routes(),
        verify_routes_preserved(),
        verify_no_order_send_added(),
    ]
    print("=" * 63)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
