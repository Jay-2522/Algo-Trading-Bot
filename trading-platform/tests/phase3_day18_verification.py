import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def eur_payload() -> dict:
    return {
        "signal_id": "life-test-001",
        "canonical_symbol": "EURUSD",
        "action": "BUY",
        "allocation_mode": "EQUAL",
        "total_lot": 0.03,
        "requested_price": 1.085,
    }


def make_queue_item():
    from backend.account_routing.allocation_monitoring_service import AllocationMonitoringService
    from backend.execution_queue.execution_queue_manager import ExecutionQueueManager

    allocation = AllocationMonitoringService().preview_allocation(eur_payload())
    manager = ExecutionQueueManager()
    return manager, manager.enqueue_from_allocation(allocation, eur_payload())[0]


def verify_files_and_routes() -> bool:
    files = [
        "backend/execution_queue/execution_lifecycle_models.py",
        "backend/execution_queue/execution_simulator.py",
        "backend/execution_queue/order_lifecycle_tracker.py",
        "backend/execution_queue/execution_audit_logger.py",
        "backend/execution_queue/execution_reconciliation_engine.py",
        "backend/execution_queue/execution_lifecycle_service.py",
        "docs/phase-3-day-18-progress.md",
    ]
    files_ok = all((PROJECT_ROOT / path).is_file() for path in files)
    try:
        from backend.main import app

        routes = {route.path for route in app.routes}
        expected = {
            "/execution-queue/lifecycle/status",
            "/execution-queue/lifecycle/items",
            "/execution-queue/lifecycle/audit-events",
            "/execution-queue/items/{queue_id}/simulate",
            "/execution-queue/simulate-latest",
            "/execution-queue/status",
        }
        routes_ok = expected <= routes
    except Exception:
        routes_ok = False
    return show("Lifecycle files and routes exist", files_ok and routes_ok)


def verify_simulator_and_reconciliation() -> bool:
    try:
        from backend.execution_queue.execution_reconciliation_engine import ExecutionReconciliationEngine
        from backend.execution_queue.execution_simulator import ExecutionSimulator

        _, item = make_queue_item()
        simulator = ExecutionSimulator()
        result = simulator.simulate_execution(item)
        invalid = item.model_copy(deep=True)
        invalid.intent.allocated_lot = 0.0
        rejected = simulator.simulate_execution(invalid)
        reconciliation = ExecutionReconciliationEngine().reconcile_simulated_execution(result)
        rejected_reconciliation = ExecutionReconciliationEngine().reconcile_simulated_execution(rejected)
        passed = (
            result.status == "SIMULATED_FILLED"
            and result.filled_lot == result.requested_lot
            and result.simulated_fill_price is not None
            and result.slippage_points > 0
            and result.simulation_only is True
            and result.live_execution_enabled is False
            and rejected.status == "SIMULATED_REJECTED"
            and "lot" in rejected.rejection_reason.lower()
            and reconciliation["reconciled"] is True
            and rejected_reconciliation["reconciled"] is False
        )
        return show("Simulator fills valid item, rejects invalid item, and reconciles safely", passed)
    except Exception as exc:
        return show("Simulator fills valid item, rejects invalid item, and reconciles safely", False, str(exc))


def verify_lifecycle_and_audit() -> bool:
    try:
        from backend.execution_queue.execution_audit_logger import ExecutionAuditLogger
        from backend.execution_queue.execution_lifecycle_service import ExecutionLifecycleService
        from backend.execution_queue.order_lifecycle_tracker import OrderLifecycleTracker

        manager, item = make_queue_item()
        tracker = OrderLifecycleTracker()
        lifecycle = tracker.create_lifecycle(item)
        tracker.update_state(item.queue_id, "VALIDATED", "Validated in test.")
        audit = ExecutionAuditLogger()
        audit.log_event(item.queue_id, "TEST_EVENT", "Audit test.", {"ok": True})
        service = ExecutionLifecycleService(queue_manager=manager)
        result = service.simulate_queue_item(item.queue_id)
        lifecycles = service.get_lifecycles()
        events = service.get_audit_events()
        passed = (
            lifecycle.current_state == "VALIDATED"
            and len(lifecycle.history) == 2
            and len(audit.get_events_for_queue(item.queue_id)) == 1
            and result.status == "SIMULATED_FILLED"
            and len(lifecycles) == 1
            and lifecycles[0].current_state == "SIMULATED_FILLED"
            and len(events) >= 2
            and service.get_status()["simulation_only"] is True
            and service.get_status()["live_execution_enabled"] is False
        )
        return show("Lifecycle tracker and audit logger record state transitions/events", passed)
    except Exception as exc:
        return show("Lifecycle tracker and audit logger record state transitions/events", False, str(exc))


def verify_api_and_safety() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        status = client.get("/execution-queue/lifecycle/status")
        enqueue = client.post("/execution-queue/enqueue-preview", json=eur_payload())
        queue_id = enqueue.json()[0]["queue_id"]
        simulate = client.post(f"/execution-queue/items/{queue_id}/simulate")
        latest_enqueue = client.post("/execution-queue/enqueue-preview", json={**eur_payload(), "signal_id": "life-test-002"})
        latest = client.post("/execution-queue/simulate-latest")
        lifecycles = client.get("/execution-queue/lifecycle/items")
        audit = client.get("/execution-queue/lifecycle/audit-events")
        queue_status = client.get("/execution-queue/status")
        safety_text = "\n".join(
            path.read_text(encoding="utf-8", errors="ignore")
            for path in (PROJECT_ROOT / "backend").rglob("*.py")
        )
        passed = (
            status.status_code == 200
            and status.json()["simulation_only"] is True
            and status.json()["live_execution_enabled"] is False
            and enqueue.status_code == 200
            and simulate.status_code == 200
            and simulate.json()["status"] == "SIMULATED_FILLED"
            and simulate.json()["simulation_only"] is True
            and simulate.json()["live_execution_enabled"] is False
            and latest_enqueue.status_code == 200
            and latest.status_code == 200
            and lifecycles.status_code == 200
            and len(lifecycles.json()) >= 2
            and audit.status_code == 200
            and len(audit.json()) >= 2
            and queue_status.status_code == 200
            and "mt5.order_send" not in safety_text
            and "order_send(" not in safety_text
            and "live_execution_enabled=True" not in safety_text
        )
        return show("Lifecycle APIs are JSON-safe and preserve execution queue routes", passed)
    except Exception as exc:
        return show("Lifecycle APIs are JSON-safe and preserve execution queue routes", False, str(exc))


def main() -> int:
    print("Phase 3 Day 18 Execution Lifecycle Verification")
    print("=" * 58)
    checks = [
        verify_files_and_routes(),
        verify_simulator_and_reconciliation(),
        verify_lifecycle_and_audit(),
        verify_api_and_safety(),
    ]
    print("=" * 58)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
