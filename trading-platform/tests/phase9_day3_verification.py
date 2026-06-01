import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def approved_signal(signal_id="mock-eur-approval-001", **overrides):
    payload = {
        "signal_id": signal_id,
        "symbol": "EURUSD",
        "action": "BUY",
        "confidence": 85.0,
        "execution_allowed": True,
        "trade_quality": "A",
        "risk_mode": "NORMAL",
        "reason": "Mock approved EURUSD signal for demo approval testing.",
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

        files = [
            "backend/strategy_execution_bridge/demo_approval_models.py",
            "backend/strategy_execution_bridge/approval_guard.py",
            "backend/strategy_execution_bridge/demo_execution_approval_store.py",
            "backend/strategy_execution_bridge/demo_execution_approval_service.py",
            "docs/phase-9-day-3-progress.md",
        ]
        missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
        route_methods = {
            route.path: set(getattr(route, "methods", set()) or set())
            for route in app.routes
        }
        expected = {
            "/strategy-execution-bridge/demo-approval/status",
            "/strategy-execution-bridge/demo-approval/approve",
            "/strategy-execution-bridge/demo-approval/approvals",
            "/strategy-execution-bridge/demo-approval/history",
            "/strategy-execution-bridge/demo-approval/approvals/{approval_id}",
            "/strategy-execution-bridge/demo-approval/candidates",
            "/strategy-execution-bridge/demo-approval/candidates/{candidate_id}",
        }
        methods_ok = (
            "GET" in route_methods.get("/strategy-execution-bridge/demo-approval/status", set())
            and "POST" in route_methods.get("/strategy-execution-bridge/demo-approval/approve", set())
            and "GET" in route_methods.get("/strategy-execution-bridge/demo-approval/approvals", set())
            and "GET" in route_methods.get("/strategy-execution-bridge/demo-approval/history", set())
            and "GET" in route_methods.get("/strategy-execution-bridge/demo-approval/approvals/{approval_id}", set())
            and "GET" in route_methods.get("/strategy-execution-bridge/demo-approval/candidates", set())
            and "GET" in route_methods.get("/strategy-execution-bridge/demo-approval/candidates/{candidate_id}", set())
        )
        return show("Demo approval files and routes exist", not missing and expected <= set(route_methods) and methods_ok, ", ".join(missing))
    except Exception as exc:
        return show("Demo approval files and routes exist", False, str(exc))


def verify_approval_rejections() -> bool:
    try:
        from backend.main import app
        from backend.strategy_execution_bridge.bridge_decision_store import BridgeDecisionStore
        from backend.strategy_execution_bridge.bridge_models import StrategyBridgeDecision, StrategyExecutionIntent

        client = TestClient(app)
        valid_preview = client.post(
            "/strategy-execution-bridge/evaluate-and-preview",
            json=approved_signal("mock-eur-unconfirmed-001"),
        ).json()
        unconfirmed = client.post(
            "/strategy-execution-bridge/demo-approval/approve",
            json={
                "decision_id": valid_preview["decision_id"],
                "confirm_demo_approval": False,
                "requested_by": "test",
                "reason": "Should reject unconfirmed.",
            },
        ).json()
        no_preview = client.post(
            "/strategy-execution-bridge/evaluate-signal",
            json=approved_signal("mock-eur-no-preview-001"),
        ).json()
        no_preview_approval = client.post(
            "/strategy-execution-bridge/demo-approval/approve",
            json={"decision_id": no_preview["decision_id"], "confirm_demo_approval": True},
        ).json()
        rejected_bridge = client.post(
            "/strategy-execution-bridge/evaluate-and-preview",
            json=approved_signal("mock-eur-wait-001", action="WAIT", confidence=10, trade_quality="NO_TRADE"),
        ).json()
        rejected_bridge_approval = client.post(
            "/strategy-execution-bridge/demo-approval/approve",
            json={"decision_id": rejected_bridge["decision_id"], "confirm_demo_approval": True},
        ).json()
        risk_rejected = client.post(
            "/strategy-execution-bridge/evaluate-and-preview",
            json=approved_signal("mock-eur-risk-001", lot=0.02),
        ).json()
        risk_rejected_approval = client.post(
            "/strategy-execution-bridge/demo-approval/approve",
            json={"decision_id": risk_rejected["decision_id"], "confirm_demo_approval": True},
        ).json()

        old_decision = BridgeDecisionStore().store_decision(
            StrategyBridgeDecision(
                signal_id="mock-eur-stale-001",
                symbol="EURUSD",
                action="BUY",
                confidence=85,
                eligible=True,
                mapped_intent=StrategyExecutionIntent(
                    source_signal_id="mock-eur-stale-001",
                    symbol="EURUSD",
                    action="BUY",
                    confidence=85,
                ),
                queue_preview_id="strategy_queue_preview_stale",
                risk_decision_id="risk_stale",
                queue_preview_created=True,
                queue_preview_status="CREATED",
                intent_status="MAPPED",
                risk_approved=True,
                bridge_status="APPROVED_FOR_QUEUE_PREVIEW",
                timestamp=datetime.now(timezone.utc) - timedelta(minutes=16),
            )
        )
        stale = client.post(
            "/strategy-execution-bridge/demo-approval/approve",
            json={"decision_id": old_decision.decision_id, "confirm_demo_approval": True},
        ).json()

        passed = (
            unconfirmed["approval_status"] == "REJECTED_NOT_CONFIRMED"
            and no_preview_approval["approval_status"] == "REJECTED_NO_QUEUE_PREVIEW"
            and rejected_bridge_approval["approval_status"] in {"REJECTED_NO_QUEUE_PREVIEW", "REJECTED_BRIDGE_NOT_APPROVED"}
            and risk_rejected_approval["approval_status"] in {"REJECTED_NO_QUEUE_PREVIEW", "REJECTED_BRIDGE_NOT_APPROVED", "REJECTED_RISK_NOT_APPROVED"}
            and stale["approval_status"] == "REJECTED_STALE_PREVIEW"
            and unconfirmed["approved"] is False
            and no_preview_approval["approved"] is False
            and stale["approved"] is False
        )
        return show("Unconfirmed, no-preview, bridge-rejected, risk-rejected, and stale approvals are blocked", passed)
    except Exception as exc:
        return show("Unconfirmed, no-preview, bridge-rejected, risk-rejected, and stale approvals are blocked", False, str(exc))


def verify_valid_approval_and_duplicate() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        preview = client.post(
            "/strategy-execution-bridge/evaluate-and-preview",
            json=approved_signal("mock-eur-valid-approval-001"),
        ).json()
        approval = client.post(
            "/strategy-execution-bridge/demo-approval/approve",
            json={
                "decision_id": preview["decision_id"],
                "confirm_demo_approval": True,
                "requested_by": "developer_test",
                "reason": "Phase 9 Day 3 approval flow verification.",
            },
        )
        approval_payload = approval.json()
        duplicate = client.post(
            "/strategy-execution-bridge/demo-approval/approve",
            json={"decision_id": preview["decision_id"], "confirm_demo_approval": True},
        ).json()
        approvals = client.get("/strategy-execution-bridge/demo-approval/approvals")
        history = client.get("/strategy-execution-bridge/demo-approval/history")
        candidates = client.get("/strategy-execution-bridge/demo-approval/candidates")
        approval_detail = client.get(f"/strategy-execution-bridge/demo-approval/approvals/{approval_payload['approval_id']}")
        candidate_detail = client.get(
            f"/strategy-execution-bridge/demo-approval/candidates/{approval_payload['demo_execution_candidate_id']}"
        )
        candidate_payload = candidate_detail.json()
        passed = (
            approval.status_code == 200
            and approval_payload["approved"] is True
            and approval_payload["approval_status"] == "APPROVED_FOR_DEMO_EXECUTION"
            and approval_payload["demo_execution_candidate_id"]
            and approval_payload["simulation_only"] is True
            and approval_payload["demo_execution"] is True
            and approval_payload["live_execution_enabled"] is False
            and approval_payload["broker_execution_enabled"] is False
            and candidate_detail.status_code == 200
            and candidate_payload["ready_for_demo_execution"] is True
            and candidate_payload["requires_final_execution_confirmation"] is True
            and candidate_payload["live_execution_enabled"] is False
            and duplicate["approval_status"] == "REJECTED_DUPLICATE_APPROVAL"
            and approvals.status_code == 200
            and history.status_code == 200
            and candidates.status_code == 200
            and approval_detail.status_code == 200
        )
        return show("Valid queue preview becomes demo candidate and duplicate approval is blocked", passed)
    except Exception as exc:
        return show("Valid queue preview becomes demo candidate and duplicate approval is blocked", False, str(exc))


def verify_status_and_safety() -> bool:
    try:
        from backend.main import app
        from tests.regression_routes_verification import REQUIRED_GET_ROUTES, REQUIRED_WEBSOCKET_ROUTES

        client = TestClient(app)
        status = client.get("/strategy-execution-bridge/demo-approval/status").json()
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
            "/strategy-execution-bridge/demo-approval/status",
            "/strategy-execution-bridge/demo-approval/approvals",
            "/strategy-execution-bridge/demo-approval/history",
            "/strategy-execution-bridge/demo-approval/candidates",
            "/execution-queue/status",
        }
        missing = sorted((REQUIRED_GET_ROUTES | required) - registered_get_routes)
        missing_ws = sorted(REQUIRED_WEBSOCKET_ROUTES - registered_websockets)
        token = "mt5." + "order_send"
        matches = []
        for path in (PROJECT_ROOT / "backend").rglob("*.py"):
            if path.is_file() and token in path.read_text(encoding="utf-8", errors="ignore"):
                matches.append(path.relative_to(PROJECT_ROOT).as_posix())
        new_files = [
            "backend/strategy_execution_bridge/demo_execution_approval_service.py",
            "backend/strategy_execution_bridge/approval_guard.py",
        ]
        demo_executor_called = any(
            "demo_executor" in (PROJECT_ROOT / path).read_text(encoding="utf-8", errors="ignore")
            for path in new_files
        )
        passed = (
            status["simulation_only"] is True
            and status["demo_execution"] is True
            and status["live_execution_enabled"] is False
            and status["broker_execution_enabled"] is False
            and status["requires_final_execution_confirmation"] is True
            and not missing
            and not missing_ws
            and matches == ["backend/demo_execution/mt5_demo_executor.py"]
            and demo_executor_called is False
        )
        detail = ", ".join(missing + missing_ws + matches)
        return show("Approval status, preserved routes, no demo executor call, and no new order_send are safe", passed, detail)
    except Exception as exc:
        return show("Approval status, preserved routes, no demo executor call, and no new order_send are safe", False, str(exc))


def main() -> int:
    print("Phase 9 Day 3 Demo Approval Flow Verification")
    print("=" * 57)
    checks = [
        verify_files_and_routes(),
        verify_approval_rejections(),
        verify_valid_approval_and_duplicate(),
        verify_status_and_safety(),
    ]
    print("=" * 57)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
