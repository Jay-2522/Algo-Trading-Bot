import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def verify_files() -> bool:
    files = [
        "backend/execution_confirmation/__init__.py",
        "backend/execution_confirmation/confirmation_models.py",
        "backend/execution_confirmation/confirmation_tracker.py",
        "backend/execution_confirmation/position_reconciliation_engine.py",
        "backend/execution_confirmation/confirmation_audit_store.py",
        "backend/execution_confirmation/confirmation_service.py",
        "backend/api/execution_confirmation_routes.py",
        "docs/phase-5-day-5-progress.md",
    ]
    return show("Execution confirmation package, router, and docs exist", all((PROJECT_ROOT / path).is_file() for path in files))


def verify_routes() -> bool:
    try:
        from backend.main import app

        routes = {route.path for route in app.routes}
        expected = {
            "/execution-confirmation/status",
            "/execution-confirmation/confirmations",
            "/execution-confirmation/confirmations/{execution_id}",
            "/execution-confirmation/reconcile",
            "/execution-confirmation/reconciliation-summary",
            "/execution-confirmation/audit-events",
            "/demo-execution/status",
            "/multi-account-execution/status",
            "/trade-copier/status",
        }
        return show("Execution confirmation routes and Day 1-Day 4 routes registered", expected <= routes)
    except Exception as exc:
        return show("Execution confirmation routes and Day 1-Day 4 routes registered", False, str(exc))


def verify_tracker() -> bool:
    try:
        from backend.demo_execution.demo_execution_models import DemoExecutionResult
        from backend.execution_confirmation.confirmation_tracker import ExecutionConfirmationTracker
        from backend.multi_account_execution.multi_account_models import AccountExecutionResult, MultiAccountDemoExecutionResult

        tracker = ExecutionConfirmationTracker()
        demo = DemoExecutionResult(
            queue_id="confirm-demo-queue",
            broker_id="STARTRADER",
            account_id="STARTRADER_DEMO_1",
            canonical_symbol="EURUSD",
            action="BUY",
            mt5_retcode=10009,
            mt5_order=12345,
            mt5_deal=67890,
            status="DEMO_FILLED",
        )
        confirmation = tracker.track_execution(demo)
        multi = MultiAccountDemoExecutionResult(
            signal_id="confirm-multi",
            canonical_symbol="EURUSD",
            action="SELL",
            account_results=[
                AccountExecutionResult(account_id="FXPRO_DEMO_1", broker_id="FXPRO", status="DEMO_REJECTED", rejection_reasons=["Rejected"]),
                AccountExecutionResult(account_id="VANTAGE_DEMO_1", broker_id="VANTAGE", status="MT5_UNAVAILABLE", rejection_reasons=["Unavailable"]),
            ],
        )
        multi_confirmations = tracker.track_execution(multi)
        passed = (
            confirmation.order_confirmed is True
            and confirmation.deal_confirmed is True
            and confirmation.position_detected is True
            and confirmation.simulation_only is True
            and confirmation.live_execution_enabled is False
            and len(multi_confirmations) == 2
            and len(tracker.list_confirmations()) == 3
            and tracker.get_confirmation(confirmation.execution_id) is not None
        )
        return show("Confirmation tracker consumes demo and multi-account results", passed)
    except Exception as exc:
        return show("Confirmation tracker consumes demo and multi-account results", False, str(exc))


def verify_reconciliation_engine() -> bool:
    try:
        from backend.execution_confirmation.confirmation_models import ExecutionConfirmation
        from backend.execution_confirmation.confirmation_tracker import ExecutionConfirmationTracker
        from backend.execution_confirmation.position_reconciliation_engine import PositionReconciliationEngine

        tracker = ExecutionConfirmationTracker()
        engine = PositionReconciliationEngine(tracker=tracker, audit_store=tracker.audit_store)
        records = [
            ExecutionConfirmation(execution_id="confirmed", mt5_order=1, mt5_deal=2, mt5_retcode=10009, order_confirmed=True, deal_confirmed=True, position_detected=True),
            ExecutionConfirmation(execution_id="missing", mt5_order=3, mt5_deal=4, mt5_retcode=10009, order_confirmed=True, deal_confirmed=True, position_detected=False),
            ExecutionConfirmation(execution_id="mismatch", mt5_order=None, mt5_deal=5, order_confirmed=False, deal_confirmed=True, position_detected=True),
            ExecutionConfirmation(execution_id="rejected", mt5_retcode="REJECTED"),
        ]
        for record in records:
            tracker.update_confirmation(record)
            engine.reconcile_confirmation(record)
        statuses = {record.execution_id: tracker.get_confirmation(record.execution_id).reconciliation_status for record in records}
        passed = (
            statuses["confirmed"] == "CONFIRMED"
            and statuses["missing"] == "MISSING_POSITION"
            and statuses["mismatch"] == "MISMATCHED"
            and statuses["rejected"] == "REJECTED"
            and len(tracker.audit_store.list_events(100)) >= 4
        )
        return show("Reconciliation engine classifies confirmed, missing, mismatched, and rejected states", passed, str(statuses))
    except Exception as exc:
        return show("Reconciliation engine classifies confirmed, missing, mismatched, and rejected states", False, str(exc))


def verify_summary_and_audit_store() -> bool:
    try:
        from backend.execution_confirmation.confirmation_audit_store import ConfirmationAuditStore
        from backend.execution_confirmation.confirmation_models import ExecutionConfirmation
        from backend.execution_confirmation.confirmation_tracker import ExecutionConfirmationTracker
        from backend.execution_confirmation.position_reconciliation_engine import PositionReconciliationEngine

        audit = ConfirmationAuditStore()
        tracker = ExecutionConfirmationTracker(audit_store=audit)
        engine = PositionReconciliationEngine(tracker=tracker, audit_store=audit)
        tracker.update_confirmation(ExecutionConfirmation(execution_id="sum-confirmed", mt5_order=1, mt5_deal=2, order_confirmed=True, deal_confirmed=True, position_detected=True))
        tracker.update_confirmation(ExecutionConfirmation(execution_id="sum-pending"))
        tracker.update_confirmation(ExecutionConfirmation(execution_id="sum-missing", mt5_order=3, mt5_deal=4, order_confirmed=True, deal_confirmed=True, position_detected=False))
        engine.reconcile_all()
        summary = engine.build_summary()
        audit.store_event("POSITION_RECONCILED", "Manual audit store verification.", "sum-confirmed")
        passed = (
            summary.total_executions == 3
            and summary.confirmed == 1
            and summary.pending == 1
            and summary.missing_position == 1
            and summary.simulation_only is True
            and summary.live_execution_enabled is False
            and len(audit.list_events(100)) >= 2
        )
        return show("Summary builder and audit store work with safety flags", passed)
    except Exception as exc:
        return show("Summary builder and audit store work with safety flags", False, str(exc))


def verify_api_and_safety_flags() -> bool:
    try:
        from backend.api.execution_confirmation_routes import execution_confirmation_service
        from backend.demo_execution.demo_execution_models import DemoExecutionResult
        from backend.main import app

        execution_confirmation_service.tracker.track_execution(
            DemoExecutionResult(
                queue_id="api-confirmation-queue",
                broker_id="STARTRADER",
                account_id="STARTRADER_DEMO_1",
                canonical_symbol="EURUSD",
                action="BUY",
                mt5_order=111,
                mt5_deal=222,
                mt5_retcode=10009,
                status="DEMO_FILLED",
            )
        )
        client = TestClient(app)
        status = client.get("/execution-confirmation/status")
        confirmations = client.get("/execution-confirmation/confirmations")
        reconcile = client.post("/execution-confirmation/reconcile")
        summary = client.get("/execution-confirmation/reconciliation-summary")
        audits = client.get("/execution-confirmation/audit-events")
        status_json = status.json()
        first_confirmation = confirmations.json()[0]
        passed = (
            status.status_code == 200
            and confirmations.status_code == 200
            and reconcile.status_code == 200
            and summary.status_code == 200
            and audits.status_code == 200
            and status_json.get("simulation_only") is True
            and status_json.get("demo_execution") is True
            and status_json.get("live_execution_enabled") is False
            and status_json.get("broker_execution_enabled") is False
            and first_confirmation.get("simulation_only") is True
            and first_confirmation.get("live_execution_enabled") is False
            and summary.json().get("simulation_only") is True
            and summary.json().get("live_execution_enabled") is False
        )
        return show("Execution confirmation APIs work and preserve safety flags", passed)
    except Exception as exc:
        return show("Execution confirmation APIs work and preserve safety flags", False, str(exc))


def verify_module_registry() -> bool:
    try:
        from backend.system_health.module_registry import get_module_registry

        modules = get_module_registry()
        passed = any(module["name"] == "execution_confirmation_tracking" and module["route"] == "/execution-confirmation/status" for module in modules)
        return show("Execution confirmation appears in module registry", passed)
    except Exception as exc:
        return show("Execution confirmation appears in module registry", False, str(exc))


def verify_order_send_isolated() -> bool:
    token = "mt5." + "order_send"
    matches = []
    for path in (PROJECT_ROOT / "backend").rglob("*.py"):
        if path.is_file() and token in path.read_text(encoding="utf-8", errors="ignore"):
            matches.append(path.relative_to(PROJECT_ROOT).as_posix())
    passed = matches == ["backend/demo_execution/mt5_demo_executor.py"]
    return show("MT5 order submission remains isolated to guarded demo executor", passed, ", ".join(matches))


def main() -> int:
    print("Phase 5 Day 5 Execution Confirmation Verification")
    print("=" * 58)
    checks = [
        verify_files(),
        verify_routes(),
        verify_tracker(),
        verify_reconciliation_engine(),
        verify_summary_and_audit_store(),
        verify_api_and_safety_flags(),
        verify_module_registry(),
        verify_order_send_isolated(),
    ]
    print("=" * 58)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
