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
        "signal_id": "queue-test-001",
        "canonical_symbol": "EURUSD",
        "action": "BUY",
        "allocation_mode": "EQUAL",
        "total_lot": 0.03,
    }


def verify_files_and_routes() -> bool:
    files = [
        "backend/execution_queue/__init__.py",
        "backend/execution_queue/execution_queue_models.py",
        "backend/execution_queue/execution_intent_builder.py",
        "backend/execution_queue/execution_queue_store.py",
        "backend/execution_queue/execution_readiness_validator.py",
        "backend/execution_queue/execution_queue_manager.py",
        "backend/execution_queue/execution_queue_service.py",
        "backend/api/execution_queue_routes.py",
        "docs/phase-3-day-17-progress.md",
    ]
    files_ok = all((PROJECT_ROOT / path).is_file() for path in files)
    try:
        from backend.main import app

        routes = {route.path for route in app.routes}
        expected = {
            "/execution-queue/status",
            "/execution-queue/items",
            "/execution-queue/items/{queue_id}",
            "/execution-queue/enqueue-preview",
            "/execution-queue/items/{queue_id}/cancel",
            "/accounts/status",
        }
        routes_ok = expected <= routes
    except Exception:
        routes_ok = False
    return show("Execution queue files and routes exist", files_ok and routes_ok)


def verify_intents_and_validator() -> bool:
    try:
        from backend.account_routing.allocation_monitoring_service import AllocationMonitoringService
        from backend.execution_queue.execution_intent_builder import ExecutionIntentBuilder
        from backend.execution_queue.execution_queue_models import ExecutionIntent
        from backend.execution_queue.execution_readiness_validator import ExecutionReadinessValidator

        allocation_service = AllocationMonitoringService()
        eur_allocation = allocation_service.preview_allocation(eur_payload())
        nifty_allocation = allocation_service.preview_allocation(
            {"signal_id": "queue-test-002", "canonical_symbol": "NIFTY50", "action": "BUY", "allocation_mode": "EQUAL", "total_lot": 1}
        )
        builder = ExecutionIntentBuilder()
        eur_intents = builder.build_intents_from_allocation(eur_allocation)
        nifty_intents = builder.build_intents_from_allocation(nifty_allocation)
        validator = ExecutionReadinessValidator()
        ready, errors, _ = validator.validate_intent(eur_intents[0])
        invalid_lot = eur_intents[0].model_copy(update={"allocated_lot": 0.0})
        invalid_action = ExecutionIntent.model_construct(
            signal_id="bad-action",
            account_id="STARTRADER_DEMO_1",
            broker_id="STARTRADER",
            canonical_symbol="EURUSD",
            broker_symbol="EURUSD",
            action="HOLD",
            allocated_lot=0.01,
            order_type="MARKET",
            simulation_only=True,
            live_execution_enabled=False,
        )
        bad_lot_ready, bad_lot_errors, _ = validator.validate_intent(invalid_lot)
        bad_action_ready, bad_action_errors, _ = validator.validate_intent(invalid_action)
        passed = (
            len(eur_intents) == 3
            and eur_intents[0].canonical_symbol == "EURUSD"
            and eur_intents[0].broker_symbol == "EURUSD"
            and eur_intents[0].allocated_lot == 0.01
            and eur_intents[0].simulation_only is True
            and eur_intents[0].live_execution_enabled is False
            and len(nifty_intents) == 0
            and ready == "READY_FOR_DEMO_QUEUE"
            and not errors
            and bad_lot_ready == "INVALID"
            and any("lot" in error.lower() for error in bad_lot_errors)
            and bad_action_ready == "INVALID"
            and any("action" in error.lower() for error in bad_action_errors)
        )
        return show("Execution intents and readiness validator behave safely", passed)
    except Exception as exc:
        return show("Execution intents and readiness validator behave safely", False, str(exc))


def verify_queue_manager_and_cancel() -> bool:
    try:
        from backend.account_routing.allocation_monitoring_service import AllocationMonitoringService
        from backend.execution_queue.execution_queue_manager import ExecutionQueueManager

        allocation = AllocationMonitoringService().preview_allocation(eur_payload())
        manager = ExecutionQueueManager()
        items = manager.enqueue_from_allocation(allocation, eur_payload())
        status = manager.get_status()
        initially_queued = all(item.status == "QUEUED" for item in items)
        initially_ready = all(item.readiness == "READY_FOR_DEMO_QUEUE" for item in items)
        cancelled = manager.cancel(items[0].queue_id, "Verification cancellation.")
        after_cancel = manager.get_status()
        passed = (
            len(items) == 3
            and initially_queued
            and initially_ready
            and status.total_items == 3
            and status.queued == 3
            and cancelled is not None
            and cancelled.status == "CANCELLED"
            and cancelled.readiness == "BLOCKED"
            and after_cancel.cancelled == 1
            and after_cancel.live_execution_enabled is False
        )
        return show("Queue manager stores items and supports cancellation", passed)
    except Exception as exc:
        return show("Queue manager stores items and supports cancellation", False, str(exc))


def verify_api_and_safety() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        status = client.get("/execution-queue/status")
        items_before = client.get("/execution-queue/items")
        enqueue = client.post("/execution-queue/enqueue-preview", json=eur_payload())
        queue_items = enqueue.json()
        fetched = client.get(f"/execution-queue/items/{queue_items[0]['queue_id']}")
        cancelled = client.post(
            f"/execution-queue/items/{queue_items[0]['queue_id']}/cancel",
            json={"reason": "API verification cancellation."},
        )
        nifty = client.post(
            "/execution-queue/enqueue-preview",
            json={"signal_id": "queue-test-003", "canonical_symbol": "NIFTY50", "action": "BUY", "allocation_mode": "EQUAL", "total_lot": 1},
        )
        accounts = client.get("/accounts/status")
        safety_text = "\n".join(
            path.read_text(encoding="utf-8", errors="ignore")
            for path in (PROJECT_ROOT / "backend").rglob("*.py")
        )
        passed = (
            status.status_code == 200
            and status.json()["simulation_only"] is True
            and status.json()["live_execution_enabled"] is False
            and items_before.status_code == 200
            and enqueue.status_code == 200
            and len(queue_items) == 3
            and queue_items[0]["simulation_only"] is True
            and queue_items[0]["live_execution_enabled"] is False
            and fetched.status_code == 200
            and cancelled.status_code == 200
            and cancelled.json()["status"] == "CANCELLED"
            and nifty.status_code == 200
            and nifty.json() == []
            and accounts.status_code == 200
            and "mt5.order_send" not in safety_text
            and "order_send(" not in safety_text
            and "live_execution_enabled=True" not in safety_text
        )
        return show("Execution queue APIs are JSON-safe and preserve account routes", passed)
    except Exception as exc:
        return show("Execution queue APIs are JSON-safe and preserve account routes", False, str(exc))


def main() -> int:
    print("Phase 3 Day 17 Execution Queue Verification")
    print("=" * 55)
    checks = [
        verify_files_and_routes(),
        verify_intents_and_validator(),
        verify_queue_manager_and_cancel(),
        verify_api_and_safety(),
    ]
    print("=" * 55)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
