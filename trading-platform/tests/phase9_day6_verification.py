import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def approved_signal(signal_id="mock-eur-copier-001", **overrides):
    payload = {
        "signal_id": signal_id,
        "symbol": "EURUSD",
        "action": "BUY",
        "confidence": 86,
        "execution_allowed": True,
        "trade_quality": "A",
        "risk_mode": "NORMAL",
        "reason": "Mock approved EURUSD signal for Phase 9 Day 6 copier testing.",
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


def create_candidate(client: TestClient, signal_id: str) -> str:
    preview = client.post("/strategy-execution-bridge/evaluate-and-preview", json=approved_signal(signal_id)).json()
    approval = client.post(
        "/strategy-execution-bridge/demo-approval/approve",
        json={
            "decision_id": preview["decision_id"],
            "confirm_demo_approval": True,
            "requested_by": "phase9_day6_test",
            "reason": "Phase 9 Day 6 approval.",
        },
    ).json()
    return approval["demo_execution_candidate_id"]


def verify_files_routes_and_model() -> bool:
    try:
        from backend.main import app
        from backend.trade_copier.copier_execution_bridge import TradeCopierExecutionResult

        files = [
            "backend/trade_copier/copier_execution_bridge.py",
            "backend/trade_copier/copier_execution_store.py",
            "docs/phase-9-day-6-progress.md",
        ]
        missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
        route_methods = {route.path: set(getattr(route, "methods", set()) or set()) for route in app.routes}
        routes_ok = (
            "GET" in route_methods.get("/trade-copier/execution-results", set())
            and "GET" in route_methods.get("/trade-copier/execution-results/{copier_execution_id}", set())
            and "POST" in route_methods.get("/trade-copier/distribute-execution", set())
        )
        model_ok = all(
            field in TradeCopierExecutionResult.model_fields
            for field in [
                "copier_execution_id",
                "source_execution_id",
                "copy_batch_id",
                "copied_accounts",
                "skipped_accounts",
                "failed_accounts",
                "duplicate_blocked",
                "copy_status",
            ]
        )
        return show("Copier execution files, model, and routes exist", not missing and routes_ok and model_ok, ", ".join(missing))
    except Exception as exc:
        return show("Copier execution files, model, and routes exist", False, str(exc))


def verify_distribution_and_duplicates() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        payload = {
            "final_execution_id": "final-copy-test-001",
            "decision_id": "signal-copy-test-001",
            "symbol": "EURUSD",
            "action": "BUY",
            "lot": 0.01,
            "execution_status": "DEMO_FILLED",
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }
        first = client.post("/trade-copier/distribute-execution", json=payload).json()
        duplicate = client.post("/trade-copier/distribute-execution", json=payload).json()
        listed = client.get("/trade-copier/execution-results").json()
        detail = client.get(f"/trade-copier/execution-results/{first['copier_execution_id']}").json()
        passed = (
            first["copy_status"] in {"COPIED", "PARTIAL_COPY"}
            and first["copy_batch_id"]
            and set(first["copied_accounts"]) == {"STARTRADER_DEMO_1", "FXPRO_DEMO_1", "VANTAGE_DEMO_1"}
            and duplicate["copy_status"] == "DUPLICATE_BLOCKED"
            and duplicate["duplicate_blocked"] is True
            and any(item["copier_execution_id"] == first["copier_execution_id"] for item in listed)
            and detail["copier_execution_id"] == first["copier_execution_id"]
            and first["simulation_only"] is True
            and first["demo_execution"] is True
            and first["live_execution_enabled"] is False
            and first["broker_execution_enabled"] is False
        )
        return show("EURUSD demo execution creates copy batch, stores result, and blocks duplicates", passed)
    except Exception as exc:
        return show("EURUSD demo execution creates copy batch, stores result, and blocks duplicates", False, str(exc))


def verify_risk_and_safety_blocks() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        oversize = client.post(
            "/trade-copier/distribute-execution",
            json={
                "final_execution_id": "final-copy-risk-001",
                "decision_id": "signal-copy-risk-001",
                "symbol": "EURUSD",
                "action": "BUY",
                "lot": 0.02,
                "simulation_only": True,
                "demo_execution": True,
                "live_execution_enabled": False,
                "broker_execution_enabled": False,
            },
        ).json()
        live_flag = client.post(
            "/trade-copier/distribute-execution",
            json={
                "final_execution_id": "final-copy-live-001",
                "decision_id": "signal-copy-live-001",
                "symbol": "EURUSD",
                "action": "BUY",
                "lot": 0.01,
                "simulation_only": True,
                "demo_execution": True,
                "live_execution_enabled": True,
                "broker_execution_enabled": False,
            },
        ).json()
        xau = client.post(
            "/trade-copier/distribute-execution",
            json={
                "final_execution_id": "final-copy-xau-001",
                "decision_id": "signal-copy-xau-001",
                "symbol": "XAUUSD",
                "action": "BUY",
                "lot": 0.01,
                "simulation_only": True,
                "demo_execution": True,
                "live_execution_enabled": False,
                "broker_execution_enabled": False,
            },
        ).json()
        passed = (
            oversize["copy_status"] == "FAILED_SAFE"
            and live_flag["copy_status"] == "FAILED_SAFE"
            and xau["copy_status"] == "FAILED_SAFE"
            and all(item["live_execution_enabled"] is False for item in [oversize, live_flag, xau])
            and all(item["broker_execution_enabled"] is False for item in [oversize, live_flag, xau])
            and all(item["simulation_only"] is True for item in [oversize, live_flag, xau])
            and all(item["demo_execution"] is True for item in [oversize, live_flag, xau])
        )
        return show("Max lot, live flag, and blocked symbol protections remain active", passed)
    except Exception as exc:
        return show("Max lot, live flag, and blocked symbol protections remain active", False, str(exc))


def verify_final_execution_link() -> bool:
    try:
        from backend.demo_execution.demo_execution_models import DemoExecutionResult
        from backend.demo_execution.demo_execution_service import DemoExecutionService
        from backend.main import app
        from backend.strategy_execution_bridge.final_demo_execution_models import FinalDemoExecutionRequest
        from backend.strategy_execution_bridge.final_demo_execution_service import FinalDemoExecutionService

        class FilledExecutor:
            def execute_demo_order(self, queue_item, request):
                return DemoExecutionResult(
                    queue_id=queue_item.queue_id,
                    broker_id="STARTRADER",
                    account_id="STARTRADER_DEMO_1",
                    canonical_symbol=queue_item.intent.canonical_symbol,
                    broker_symbol=queue_item.intent.broker_symbol,
                    action=queue_item.intent.action,
                    requested_lot=queue_item.intent.allocated_lot,
                    executed_lot=queue_item.intent.allocated_lot,
                    status="DEMO_FILLED",
                    mt5_retcode=10009,
                    mt5_order=123456,
                    mt5_deal=789012,
                    demo_execution=True,
                    simulation_only=True,
                    live_execution_enabled=False,
                    broker_execution_enabled=False,
                )

        client = TestClient(app)
        candidate_id = create_candidate(client, "mock-eur-copier-final-link")
        service = FinalDemoExecutionService(demo_execution_service=DemoExecutionService(executor=FilledExecutor()))
        decision = service.execute_candidate(
            FinalDemoExecutionRequest(
                candidate_id=candidate_id,
                confirm_demo_execution=True,
                requested_by="phase9_day6_test",
                reason="Verify final execution to copier batch link.",
            )
        )
        passed = (
            decision.execution_status == "DEMO_FILLED"
            and decision.copy_batch_id is not None
            and decision.copier_execution_id is not None
            and decision.simulation_only is True
            and decision.demo_execution is True
            and decision.live_execution_enabled is False
            and decision.broker_execution_enabled is False
        )
        return show("Final demo execution links filled EURUSD decisions to copier batch", passed)
    except Exception as exc:
        return show("Final demo execution links filled EURUSD decisions to copier batch", False, str(exc))


def verify_preserved_routes_and_order_send_safety() -> bool:
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
            "/trade-copier/status",
            "/trade-copier/batches",
            "/trade-copier/execution-results",
            "/strategy-execution-bridge/status",
            "/strategy-execution-bridge/e2e/status",
            "/execution-risk/status",
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
        return show("Existing routes and order_send isolation are preserved", passed, ", ".join(missing + missing_ws + matches))
    except Exception as exc:
        return show("Existing routes and order_send isolation are preserved", False, str(exc))


def main() -> int:
    print("Phase 9 Day 6 Multi-Account Demo Trade Copier Verification")
    print("=" * 66)
    checks = [
        verify_files_routes_and_model(),
        verify_distribution_and_duplicates(),
        verify_risk_and_safety_blocks(),
        verify_final_execution_link(),
        verify_preserved_routes_and_order_send_safety(),
    ]
    print("=" * 66)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
