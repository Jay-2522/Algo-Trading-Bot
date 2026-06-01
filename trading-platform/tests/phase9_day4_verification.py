import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def approved_signal(signal_id="mock-eur-final-001", **overrides):
    payload = {
        "signal_id": signal_id,
        "symbol": "EURUSD",
        "action": "BUY",
        "confidence": 85,
        "execution_allowed": True,
        "trade_quality": "A",
        "risk_mode": "NORMAL",
        "reason": "Mock approved EURUSD signal for final demo execution testing.",
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


def create_candidate(client: TestClient, signal_id: str = "mock-eur-final-001") -> str:
    preview = client.post(
        "/strategy-execution-bridge/evaluate-and-preview",
        json=approved_signal(signal_id),
    ).json()
    approval = client.post(
        "/strategy-execution-bridge/demo-approval/approve",
        json={
            "decision_id": preview["decision_id"],
            "confirm_demo_approval": True,
            "requested_by": "developer_test",
            "reason": "Phase 9 Day 4 approval.",
        },
    ).json()
    return approval["demo_execution_candidate_id"]


def verify_files_and_routes() -> bool:
    try:
        from backend.main import app

        files = [
            "backend/strategy_execution_bridge/final_demo_execution_models.py",
            "backend/strategy_execution_bridge/final_demo_execution_guard.py",
            "backend/strategy_execution_bridge/final_demo_execution_store.py",
            "backend/strategy_execution_bridge/final_demo_execution_service.py",
            "docs/phase-9-day-4-progress.md",
        ]
        missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
        route_methods = {route.path: set(getattr(route, "methods", set()) or set()) for route in app.routes}
        routes_ok = (
            "GET" in route_methods.get("/strategy-execution-bridge/final-demo-execution/status", set())
            and "POST" in route_methods.get("/strategy-execution-bridge/final-demo-execution/execute", set())
            and "GET" in route_methods.get("/strategy-execution-bridge/final-demo-execution/executions", set())
            and "GET" in route_methods.get("/strategy-execution-bridge/final-demo-execution/executions/{final_execution_id}", set())
        )
        return show("Final demo execution files and routes exist", not missing and routes_ok, ", ".join(missing))
    except Exception as exc:
        return show("Final demo execution files and routes exist", False, str(exc))


def verify_blocking_paths() -> bool:
    try:
        from backend.main import app
        from backend.strategy_execution_bridge.demo_approval_models import DemoExecutionCandidate
        from backend.strategy_execution_bridge.demo_execution_approval_store import DemoExecutionApprovalStore

        client = TestClient(app)
        candidate_id = create_candidate(client, "mock-eur-unconfirmed-final-001")
        unconfirmed = client.post(
            "/strategy-execution-bridge/final-demo-execution/execute",
            json={"candidate_id": candidate_id, "confirm_demo_execution": False},
        ).json()
        missing = client.post(
            "/strategy-execution-bridge/final-demo-execution/execute",
            json={"candidate_id": "missing-candidate", "confirm_demo_execution": True},
        ).json()
        store = DemoExecutionApprovalStore()
        unapproved_candidate = store.store_candidate(
            DemoExecutionCandidate(
                approval_id="approval-unapproved",
                decision_id="decision-unapproved",
                queue_preview_id="preview-unapproved",
                symbol="EURUSD",
                action="BUY",
                ready_for_demo_execution=False,
            )
        )
        unapproved = client.post(
            "/strategy-execution-bridge/final-demo-execution/execute",
            json={"candidate_id": unapproved_candidate.candidate_id, "confirm_demo_execution": True},
        ).json()
        stale_candidate = store.store_candidate(
            DemoExecutionCandidate(
                approval_id="approval-stale",
                decision_id="decision-stale",
                queue_preview_id="preview-stale",
                symbol="EURUSD",
                action="BUY",
                timestamp=datetime.now(timezone.utc) - timedelta(minutes=16),
            )
        )
        stale = client.post(
            "/strategy-execution-bridge/final-demo-execution/execute",
            json={"candidate_id": stale_candidate.candidate_id, "confirm_demo_execution": True},
        ).json()
        risk_candidate = store.store_candidate(
            DemoExecutionCandidate(
                approval_id="approval-risk",
                decision_id="decision-risk",
                queue_preview_id="preview-risk",
                symbol="EURUSD",
                action="BUY",
                lot=0.02,
            )
        )
        risk = client.post(
            "/strategy-execution-bridge/final-demo-execution/execute",
            json={"candidate_id": risk_candidate.candidate_id, "confirm_demo_execution": True},
        ).json()
        xau_candidate = store.store_candidate(
            DemoExecutionCandidate(
                approval_id="approval-xau",
                decision_id="decision-xau",
                queue_preview_id="preview-xau",
                symbol="XAUUSD",
                action="BUY",
            )
        )
        xau = client.post(
            "/strategy-execution-bridge/final-demo-execution/execute",
            json={"candidate_id": xau_candidate.candidate_id, "confirm_demo_execution": True},
        ).json()
        passed = (
            unconfirmed["execution_status"] == "BLOCKED_NOT_CONFIRMED"
            and missing["execution_status"] == "BLOCKED_CANDIDATE_NOT_FOUND"
            and unapproved["execution_status"] == "BLOCKED_CANDIDATE_NOT_APPROVED"
            and stale["execution_status"] == "BLOCKED_STALE_CANDIDATE"
            and risk["execution_status"] == "BLOCKED_RISK_ENGINE"
            and xau["execution_status"] == "BLOCKED_DEMO_GUARD"
            and all(item["approved_for_execution"] is False for item in [unconfirmed, missing, unapproved, stale, risk, xau])
        )
        return show("Unconfirmed, missing, unapproved, stale, risk-rejected, and XAUUSD candidates are blocked", passed)
    except Exception as exc:
        return show("Unconfirmed, missing, unapproved, stale, risk-rejected, and XAUUSD candidates are blocked", False, str(exc))


def verify_valid_execution_and_duplicate() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        candidate_id = create_candidate(client, "mock-eur-valid-final-001")
        first = client.post(
            "/strategy-execution-bridge/final-demo-execution/execute",
            json={
                "candidate_id": candidate_id,
                "confirm_demo_execution": True,
                "requested_by": "developer_test",
                "reason": "Phase 9 Day 4 final demo execution test.",
            },
        )
        first_payload = first.json()
        duplicate = client.post(
            "/strategy-execution-bridge/final-demo-execution/execute",
            json={"candidate_id": candidate_id, "confirm_demo_execution": True},
        ).json()
        executions = client.get("/strategy-execution-bridge/final-demo-execution/executions")
        detail = client.get(
            f"/strategy-execution-bridge/final-demo-execution/executions/{first_payload['final_execution_id']}"
        )
        acceptable_statuses = {
            "DEMO_FILLED",
            "DEMO_REJECTED",
            "MT5_UNAVAILABLE",
            "BLOCKED_DEMO_GUARD",
            "FAILED_SAFE",
        }
        passed = (
            first.status_code == 200
            and first_payload["execution_status"] in acceptable_statuses
            and first_payload["candidate_id"] == candidate_id
            and first_payload["approval_id"]
            and first_payload["decision_id"]
            and first_payload["queue_preview_id"]
            and first_payload["risk_decision_id"]
            and first_payload["demo_execution_result_id"] if first_payload["execution_status"] in {"DEMO_FILLED", "DEMO_REJECTED", "MT5_UNAVAILABLE", "BLOCKED_DEMO_GUARD", "FAILED_SAFE"} else True
        )
        passed = (
            passed
            and first_payload["simulation_only"] is True
            and first_payload["demo_execution"] is True
            and first_payload["live_execution_enabled"] is False
            and first_payload["broker_execution_enabled"] is False
            and duplicate["execution_status"] == "BLOCKED_DUPLICATE_EXECUTION"
            and executions.status_code == 200
            and detail.status_code == 200
            and detail.json()["final_execution_id"] == first_payload["final_execution_id"]
        )
        return show("Valid EURUSD candidate reaches guarded demo executor path and duplicate execution is blocked", passed)
    except Exception as exc:
        return show("Valid EURUSD candidate reaches guarded demo executor path and duplicate execution is blocked", False, str(exc))


def verify_status_safety_and_preserved_routes() -> bool:
    try:
        from backend.main import app
        from tests.regression_routes_verification import REQUIRED_GET_ROUTES, REQUIRED_WEBSOCKET_ROUTES

        client = TestClient(app)
        status = client.get("/strategy-execution-bridge/final-demo-execution/status").json()
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
            "/strategy-execution-bridge/final-demo-execution/executions",
            "/demo-execution/status",
            "/demo-execution/eligible-queue-items",
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
            and not missing
            and not missing_ws
            and matches == ["backend/demo_execution/mt5_demo_executor.py"]
        )
        return show("Final execution status, preserved routes, and order_send safety are intact", passed, ", ".join(missing + missing_ws + matches))
    except Exception as exc:
        return show("Final execution status, preserved routes, and order_send safety are intact", False, str(exc))


def main() -> int:
    print("Phase 9 Day 4 Final Demo Execution Verification")
    print("=" * 58)
    checks = [
        verify_files_and_routes(),
        verify_blocking_paths(),
        verify_valid_execution_and_duplicate(),
        verify_status_safety_and_preserved_routes(),
    ]
    print("=" * 58)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
