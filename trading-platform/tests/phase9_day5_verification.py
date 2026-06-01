import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def approved_signal(signal_id="mock-eur-e2e-001", **overrides):
    payload = {
        "signal_id": signal_id,
        "symbol": "EURUSD",
        "action": "BUY",
        "confidence": 86,
        "execution_allowed": True,
        "trade_quality": "A",
        "risk_mode": "NORMAL",
        "reason": "Mock approved EURUSD signal for Phase 9 Day 5 end-to-end flow.",
        "suggested_lot": 0.01,
        "metadata": {
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
        from backend.strategy_execution_bridge.end_to_end_demo_flow import EndToEndDemoFlowResult

        files = [
            "backend/strategy_execution_bridge/end_to_end_demo_flow.py",
            "backend/strategy_execution_bridge/end_to_end_flow_store.py",
            "docs/phase-9-day-5-progress.md",
        ]
        missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
        route_methods = {route.path: set(getattr(route, "methods", set()) or set()) for route in app.routes}
        routes_ok = (
            "GET" in route_methods.get("/strategy-execution-bridge/e2e/status", set())
            and "POST" in route_methods.get("/strategy-execution-bridge/e2e/mock-eurusd-demo", set())
            and "POST" in route_methods.get("/strategy-execution-bridge/e2e/run-signal", set())
            and "GET" in route_methods.get("/strategy-execution-bridge/e2e/flows", set())
            and "GET" in route_methods.get("/strategy-execution-bridge/e2e/flows/{flow_id}", set())
        )
        model_ok = all(
            field in EndToEndDemoFlowResult.model_fields
            for field in [
                "flow_id",
                "bridge_decision_id",
                "queue_preview_id",
                "approval_id",
                "candidate_id",
                "final_execution_id",
                "demo_execution_result_id",
                "confirmation_id",
                "final_status",
            ]
        )
        return show("End-to-end files, model, and routes exist", not missing and routes_ok and model_ok, ", ".join(missing))
    except Exception as exc:
        return show("End-to-end files, model, and routes exist", False, str(exc))


def verify_mock_eurusd_flow() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        response = client.post("/strategy-execution-bridge/e2e/mock-eurusd-demo")
        payload = response.json()
        acceptable_statuses = {
            "COMPLETED_DEMO_FILLED",
            "COMPLETED_DEMO_REJECTED",
            "COMPLETED_MT5_UNAVAILABLE",
            "BLOCKED_AT_FINAL_CONFIRMATION",
            "FAILED_SAFE",
        }
        required_steps = {
            "strategy_signal",
            "bridge_validation",
            "execution_intent",
            "risk_evaluation",
            "queue_preview",
            "demo_approval",
            "demo_candidate",
            "final_execution_confirmation",
        }
        flows = client.get("/strategy-execution-bridge/e2e/flows")
        detail = client.get(f"/strategy-execution-bridge/e2e/flows/{payload['flow_id']}")
        passed = (
            response.status_code == 200
            and payload["final_status"] in acceptable_statuses
            and payload["bridge_decision_id"]
            and payload["intent_id"]
            and payload["risk_decision_id"]
            and payload["queue_preview_id"]
            and payload["approval_id"]
            and payload["candidate_id"]
            and payload["final_execution_id"]
            and set(payload["completed_steps"]).issuperset(required_steps)
            and payload["simulation_only"] is True
            and payload["demo_execution"] is True
            and payload["live_execution_enabled"] is False
            and payload["broker_execution_enabled"] is False
            and flows.status_code == 200
            and any(flow["flow_id"] == payload["flow_id"] for flow in flows.json())
            and detail.status_code == 200
            and detail.json()["flow_id"] == payload["flow_id"]
        )
        if payload["final_status"].startswith("COMPLETED_"):
            passed = passed and payload["demo_execution_result_id"] and payload["confirmation_id"]
        return show("Mock EURUSD demo flow runs safely and stores full audit result", passed, payload.get("final_status", ""))
    except Exception as exc:
        return show("Mock EURUSD demo flow runs safely and stores full audit result", False, str(exc))


def verify_blocking_paths() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        wait_signal = client.post(
            "/strategy-execution-bridge/e2e/run-signal",
            json=approved_signal("mock-eur-e2e-wait", action="WAIT", confidence=90),
        ).json()
        low_confidence = client.post(
            "/strategy-execution-bridge/e2e/run-signal",
            json=approved_signal("mock-eur-e2e-low-confidence", confidence=50),
        ).json()
        risk_rejected = client.post(
            "/strategy-execution-bridge/e2e/run-signal",
            json=approved_signal("mock-eur-e2e-risk", suggested_lot=0.02),
        ).json()
        passed = (
            wait_signal["final_status"] == "BLOCKED_AT_BRIDGE"
            and wait_signal["failed_step"] == "bridge_validation"
            and low_confidence["final_status"] == "BLOCKED_AT_BRIDGE"
            and low_confidence["failed_step"] == "bridge_validation"
            and risk_rejected["final_status"] == "BLOCKED_AT_RISK"
            and risk_rejected["failed_step"] == "risk_evaluation"
            and not wait_signal["approval_id"]
            and not low_confidence["approval_id"]
            and not risk_rejected["approval_id"]
            and all(item["simulation_only"] is True for item in [wait_signal, low_confidence, risk_rejected])
            and all(item["demo_execution"] is True for item in [wait_signal, low_confidence, risk_rejected])
            and all(item["live_execution_enabled"] is False for item in [wait_signal, low_confidence, risk_rejected])
            and all(item["broker_execution_enabled"] is False for item in [wait_signal, low_confidence, risk_rejected])
        )
        return show("WAIT, low confidence, and risk rejection block before approval", passed)
    except Exception as exc:
        return show("WAIT, low confidence, and risk rejection block before approval", False, str(exc))


def verify_status_safety_and_preserved_routes() -> bool:
    try:
        from backend.main import app
        from tests.regression_routes_verification import REQUIRED_GET_ROUTES, REQUIRED_WEBSOCKET_ROUTES

        client = TestClient(app)
        status = client.get("/strategy-execution-bridge/e2e/status").json()
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
            "/strategy-execution-bridge/demo-approval/status",
            "/strategy-execution-bridge/final-demo-execution/status",
            "/strategy-execution-bridge/e2e/status",
            "/strategy-execution-bridge/e2e/flows",
            "/demo-execution/status",
            "/demo-execution/eligible-queue-items",
            "/execution-confirmation/status",
            "/execution-confirmation/confirmations",
        }
        missing = sorted((REQUIRED_GET_ROUTES | required) - registered_get_routes)
        missing_ws = sorted(REQUIRED_WEBSOCKET_ROUTES - registered_websockets)
        token = "mt5." + "order_send"
        matches = []
        for path in (PROJECT_ROOT / "backend").rglob("*.py"):
            if path.is_file() and token in path.read_text(encoding="utf-8", errors="ignore"):
                matches.append(path.relative_to(PROJECT_ROOT).as_posix())
        passed = (
            status["simulation_only"] is True
            and status["demo_execution"] is True
            and status["live_execution_enabled"] is False
            and status["broker_execution_enabled"] is False
            and status["final_confirmation_required"] is True
            and not missing
            and not missing_ws
            and matches == ["backend/demo_execution/mt5_demo_executor.py"]
        )
        return show("Safety flags, preserved routes, confirmation routes, and order_send isolation are intact", passed, ", ".join(missing + missing_ws + matches))
    except Exception as exc:
        return show("Safety flags, preserved routes, confirmation routes, and order_send isolation are intact", False, str(exc))


def main() -> int:
    print("Phase 9 Day 5 End-to-End Demo Flow Verification")
    print("=" * 62)
    checks = [
        verify_files_and_routes(),
        verify_mock_eurusd_flow(),
        verify_blocking_paths(),
        verify_status_safety_and_preserved_routes(),
    ]
    print("=" * 62)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
