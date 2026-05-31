import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def approved_signal(symbol="EURUSD", action="BUY", **overrides):
    payload = {
        "signal_id": f"mock-{symbol.lower()}-{action.lower()}-001",
        "symbol": symbol,
        "action": action,
        "confidence": 85.0,
        "execution_allowed": True,
        "trade_quality": "A",
        "risk_mode": "NORMAL",
        "reason": "Mock approved strategy signal for queue preview testing.",
        "metadata": {
            "strategy": symbol,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        },
        "news_context": {"high_impact_event_active": False, "trade_action": "ALLOW", "risk_level": "LOW"},
        "regime_context": {"risk_mode": "NORMAL"},
    }
    payload.update(overrides)
    return payload


def verify_files_and_routes() -> bool:
    try:
        from backend.main import app

        files = ["backend/strategy_execution_bridge/queue_preview_adapter.py"]
        missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
        route_paths = {route.path for route in app.routes}
        expected_routes = {
            "/strategy-execution-bridge/preview-signal",
            "/strategy-execution-bridge/evaluate-and-preview",
            "/strategy-execution-bridge/status",
            "/strategy-execution-bridge/evaluate-signal",
            "/strategy-execution-bridge/xauusd/latest",
            "/strategy-execution-bridge/eurusd/latest",
            "/strategy-execution-bridge/decisions",
        }
        return show("Queue preview adapter exists and bridge routes are registered", not missing and expected_routes <= route_paths, ", ".join(missing))
    except Exception as exc:
        return show("Queue preview adapter exists and bridge routes are registered", False, str(exc))


def verify_approved_eurusd_previews() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        buy = client.post("/strategy-execution-bridge/evaluate-and-preview", json=approved_signal("EURUSD", "BUY"))
        sell = client.post("/strategy-execution-bridge/preview-signal", json=approved_signal("EURUSD", "SELL"))
        buy_payload = buy.json()
        sell_payload = sell.json()
        passed = (
            buy.status_code == 200
            and buy_payload["eligible"] is True
            and buy_payload["mapped_intent"] is not None
            and buy_payload["risk_approved"] is True
            and buy_payload["queue_preview_created"] is True
            and buy_payload["queue_preview_status"] == "CREATED"
            and buy_payload["queue_preview_id"]
            and buy_payload["simulation_only"] is True
            and buy_payload["demo_execution"] is True
            and buy_payload["live_execution_enabled"] is False
            and buy_payload["broker_execution_enabled"] is False
            and sell.status_code == 200
            and sell_payload["eligible"] is True
            and sell_payload["mapped_intent"]["action"] == "SELL"
            and sell_payload["queue_preview_created"] is True
            and sell_payload["queue_preview_id"]
        )
        return show("Approved EURUSD BUY/SELL mock signals create queue previews safely", passed)
    except Exception as exc:
        return show("Approved EURUSD BUY/SELL mock signals create queue previews safely", False, str(exc))


def verify_xauusd_policy_behavior() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        response = client.post("/strategy-execution-bridge/evaluate-and-preview", json=approved_signal("XAUUSD", "BUY"))
        payload = response.json()
        passed = (
            response.status_code == 200
            and payload["eligible"] is False
            and payload["bridge_status"] == "REJECTED_RISK_ENGINE"
            and payload["risk_approved"] is False
            and payload["queue_preview_created"] is False
            and payload["queue_preview_id"] is None
            and any("blocked" in reason.lower() or "allows eurusd only" in reason.lower() for reason in payload["rejection_reasons"])
        )
        return show("Approved mock XAUUSD behavior is safe under current risk policy", passed)
    except Exception as exc:
        return show("Approved mock XAUUSD behavior is safe under current risk policy", False, str(exc))


def verify_rejections_prevent_previews() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        wait = client.post("/strategy-execution-bridge/evaluate-and-preview", json=approved_signal(action="WAIT", confidence=10, trade_quality="NO_TRADE"))
        low = client.post("/strategy-execution-bridge/evaluate-and-preview", json=approved_signal(confidence=50, trade_quality="C"))
        disabled = client.post("/strategy-execution-bridge/evaluate-and-preview", json=approved_signal(execution_allowed=False))
        lot = client.post("/strategy-execution-bridge/evaluate-and-preview", json=approved_signal(lot=0.02))
        passed = (
            wait.json()["bridge_status"] == "REJECTED_WAIT_SIGNAL"
            and wait.json()["queue_preview_created"] is False
            and low.json()["bridge_status"] == "REJECTED_LOW_CONFIDENCE"
            and low.json()["queue_preview_created"] is False
            and disabled.json()["bridge_status"] == "REJECTED_EXECUTION_NOT_ALLOWED"
            and disabled.json()["queue_preview_created"] is False
            and lot.json()["bridge_status"] == "REJECTED_RISK_ENGINE"
            and lot.json()["risk_approved"] is False
            and lot.json()["queue_preview_created"] is False
            and lot.json()["queue_preview_id"] is None
        )
        return show("WAIT, low confidence, execution disabled, and oversized lot prevent previews", passed)
    except Exception as exc:
        return show("WAIT, low confidence, execution disabled, and oversized lot prevent previews", False, str(exc))


def verify_no_execution_and_routes_preserved() -> bool:
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
        required = {
            "/strategy-execution-bridge/status",
            "/strategy-execution-bridge/decisions",
            "/strategy/eurusd/confluence",
            "/execution-queue/status",
            "/news/phase7/status",
        }
        missing = sorted((REQUIRED_GET_ROUTES | required) - registered_get_routes)
        missing_ws = sorted(REQUIRED_WEBSOCKET_ROUTES - registered_websockets)
        token = "mt5." + "order_send"
        matches = []
        for path in (PROJECT_ROOT / "backend").rglob("*.py"):
            if path.is_file() and token in path.read_text(encoding="utf-8", errors="ignore"):
                matches.append(path.relative_to(PROJECT_ROOT).as_posix())
        passed = not missing and not missing_ws and matches == ["backend/demo_execution/mt5_demo_executor.py"]
        detail = ", ".join(missing + missing_ws + matches)
        return show("No execution added and Phase 9 Day 1, Phase 8, and execution queue routes are preserved", passed, detail)
    except Exception as exc:
        return show("No execution added and Phase 9 Day 1, Phase 8, and execution queue routes are preserved", False, str(exc))


def main() -> int:
    print("Phase 9 Day 2 Execution Intent Queue Preview Verification")
    print("=" * 66)
    checks = [
        verify_files_and_routes(),
        verify_approved_eurusd_previews(),
        verify_xauusd_policy_behavior(),
        verify_rejections_prevent_previews(),
        verify_no_execution_and_routes_preserved(),
    ]
    print("=" * 66)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
