import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def approved_signal(signal_id="mock-eur-ops-001", **overrides):
    payload = {
        "signal_id": signal_id,
        "symbol": "EURUSD",
        "action": "BUY",
        "confidence": 86,
        "execution_allowed": True,
        "trade_quality": "A",
        "risk_mode": "NORMAL",
        "reason": "Mock approved EURUSD signal for operations center verification.",
        "suggested_lot": 0.01,
        "metadata": {"simulation_only": True, "live_execution_enabled": False, "broker_execution_enabled": False},
        "news_context": {"high_impact_event_active": False, "trade_action": "ALLOW", "risk_level": "LOW"},
        "regime_context": {"risk_mode": "NORMAL"},
    }
    payload.update(overrides)
    return payload


def seed_pipeline(client: TestClient) -> None:
    client.post("/strategy-execution-bridge/evaluate-and-preview", json=approved_signal("mock-eur-ops-approved"))
    client.post(
        "/strategy-execution-bridge/evaluate-and-preview",
        json=approved_signal("mock-eur-ops-rejected", action="WAIT", confidence=90),
    )
    client.post(
        "/trade-copier/distribute-execution",
        json={
            "final_execution_id": "final-ops-copy-001",
            "decision_id": "signal-ops-copy-001",
            "symbol": "EURUSD",
            "action": "BUY",
            "lot": 0.01,
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        },
    )


def verify_files_and_routes() -> bool:
    try:
        from backend.main import app

        files = [
            "backend/strategy_execution_bridge/execution_operations_models.py",
            "backend/strategy_execution_bridge/execution_operations_center.py",
            "backend/strategy_execution_bridge/execution_operations_audit.py",
            "docs/phase-9-day-7-progress.md",
        ]
        missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
        routes = {route.path: set(getattr(route, "methods", set()) or set()) for route in app.routes}
        required = [
            "/strategy-execution-bridge/operations/status",
            "/strategy-execution-bridge/operations/overview",
            "/strategy-execution-bridge/operations/pipeline-events",
            "/strategy-execution-bridge/operations/recent-executions",
            "/strategy-execution-bridge/operations/recent-rejections",
            "/strategy-execution-bridge/operations/readiness",
            "/strategy-execution-bridge/operations/health",
        ]
        routes_ok = all("GET" in routes.get(route, set()) for route in required)
        return show("Operations files and routes exist", not missing and routes_ok, ", ".join(missing))
    except Exception as exc:
        return show("Operations files and routes exist", False, str(exc))


def verify_models() -> bool:
    try:
        from backend.strategy_execution_bridge.execution_operations_models import (
            ExecutionOperationsOverview,
            ExecutionPipelineEvent,
        )

        overview_fields = {
            "status",
            "pipeline_ready",
            "bridge_ready",
            "queue_preview_ready",
            "approval_ready",
            "final_execution_ready",
            "copier_ready",
            "confirmation_ready",
            "total_bridge_decisions",
            "total_queue_previews",
            "total_approvals",
            "total_candidates",
            "total_final_executions",
            "total_copy_results",
            "blocked_count",
            "rejected_count",
            "demo_execution_count",
            "health_score",
        }
        event_fields = {"event_id", "stage", "status", "entity_id", "symbol", "action", "message", "severity", "timestamp"}
        passed = overview_fields.issubset(ExecutionOperationsOverview.model_fields) and event_fields.issubset(
            ExecutionPipelineEvent.model_fields
        )
        return show("Operations overview and pipeline event models exist", passed)
    except Exception as exc:
        return show("Operations overview and pipeline event models exist", False, str(exc))


def verify_endpoints_and_aggregation() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        seed_pipeline(client)
        status = client.get("/strategy-execution-bridge/operations/status")
        overview = client.get("/strategy-execution-bridge/operations/overview")
        events = client.get("/strategy-execution-bridge/operations/pipeline-events")
        executions = client.get("/strategy-execution-bridge/operations/recent-executions")
        rejections = client.get("/strategy-execution-bridge/operations/recent-rejections")
        readiness = client.get("/strategy-execution-bridge/operations/readiness")
        health = client.get("/strategy-execution-bridge/operations/health")

        status_payload = status.json()
        overview_payload = overview.json()
        readiness_payload = readiness.json()
        health_payload = health.json()
        passed = (
            status.status_code == 200
            and overview.status_code == 200
            and events.status_code == 200
            and executions.status_code == 200
            and rejections.status_code == 200
            and readiness.status_code == 200
            and health.status_code == 200
            and status_payload["status"] == "OPERATIONAL"
            and status_payload["pipeline_ready"] is True
            and overview_payload["total_bridge_decisions"] >= 2
            and overview_payload["total_queue_previews"] >= 1
            and overview_payload["total_copy_results"] >= 1
            and overview_payload["health_score"] == 100
            and isinstance(events.json(), list)
            and isinstance(rejections.json(), list)
            and "final_executions" in executions.json()
            and "copy_results" in executions.json()
            and readiness_payload["pipeline_ready"] is True
            and health_payload["health_score"] == 100
        )
        safety = all(
            payload["simulation_only"] is True
            and payload["demo_execution"] is True
            and payload["live_execution_enabled"] is False
            and payload["broker_execution_enabled"] is False
            for payload in [status_payload, overview_payload, readiness_payload, health_payload]
        )
        return show("Operations endpoints work, aggregate counts, and preserve safety flags", passed and safety)
    except Exception as exc:
        return show("Operations endpoints work, aggregate counts, and preserve safety flags", False, str(exc))


def verify_audit_and_module_registry() -> bool:
    try:
        from backend.strategy_execution_bridge.execution_operations_audit import ExecutionOperationsAudit
        from backend.strategy_execution_bridge.execution_operations_models import ExecutionPipelineEvent
        from backend.system_health.module_registry import get_module_registry

        audit = ExecutionOperationsAudit()
        event = audit.store_event(
            ExecutionPipelineEvent(
                stage="CONFIRMATION",
                status="AUDIT_TEST",
                entity_id="audit-test",
                symbol="EURUSD",
                action="BUY",
                message="Operations audit verification event.",
            )
        )
        registry_routes = {item["route"] for item in get_module_registry()}
        passed = (
            event.event_id
            and any(item.event_id == event.event_id for item in audit.list_events())
            and "/strategy-execution-bridge/operations/status" in registry_routes
        )
        return show("Operations audit records events and module registry includes operations center", passed)
    except Exception as exc:
        return show("Operations audit records events and module registry includes operations center", False, str(exc))


def verify_preserved_routes_and_order_send_safety() -> bool:
    try:
        from backend.main import app
        from tests.regression_routes_verification import REQUIRED_GET_ROUTES, REQUIRED_WEBSOCKET_ROUTES

        registered_get_routes = {
            route.path for route in app.routes if hasattr(route, "methods") and "GET" in route.methods
        }
        registered_websockets = {
            route.path for route in app.routes if route.__class__.__name__ == "APIWebSocketRoute"
        }
        required = {
            "/strategy-execution-bridge/status",
            "/strategy-execution-bridge/e2e/status",
            "/strategy-execution-bridge/operations/status",
            "/trade-copier/status",
            "/trade-copier/execution-results",
            "/demo-execution/status",
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
        passed = not missing and not missing_ws and matches == ["backend/demo_execution/mt5_demo_executor.py"]
        return show("Phase 9, trade copier, demo execution, confirmation routes and order_send isolation are preserved", passed, ", ".join(missing + missing_ws + matches))
    except Exception as exc:
        return show("Phase 9, trade copier, demo execution, confirmation routes and order_send isolation are preserved", False, str(exc))


def main() -> int:
    print("Phase 9 Day 7 Execution Operations Control Center Verification")
    print("=" * 70)
    checks = [
        verify_files_and_routes(),
        verify_models(),
        verify_endpoints_and_aggregation(),
        verify_audit_and_module_registry(),
        verify_preserved_routes_and_order_send_safety(),
    ]
    print("=" * 70)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
