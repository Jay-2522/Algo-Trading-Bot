import sys
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def _queue_item(symbol: str = "EURUSD", lot: float = 0.01, action: str = "BUY"):
    from backend.execution_queue.execution_queue_models import ExecutionIntent, ExecutionQueueItem

    intent = ExecutionIntent(
        signal_id=f"day2-{symbol}-{lot}-{action}",
        account_id="STARTRADER_DEMO_1",
        broker_id="STARTRADER",
        canonical_symbol=symbol,
        broker_symbol=symbol,
        action=action,
        allocated_lot=lot,
        order_type="MARKET",
        requested_price=1.085,
    )
    return ExecutionQueueItem(intent=intent, status="QUEUED", readiness="READY_FOR_DEMO_QUEUE")


class _FakeMT5:
    ACCOUNT_TRADE_MODE_DEMO = 0
    TRADE_ACTION_DEAL = 1
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    ORDER_TIME_GTC = 0
    ORDER_FILLING_IOC = 1
    TRADE_RETCODE_DONE = 10009
    TRADE_RETCODE_PLACED = 10008

    def symbol_info_tick(self, symbol: str):
        return SimpleNamespace(ask=1.0851, bid=1.0850)

    def order_send(self, request: dict):
        return SimpleNamespace(retcode=self.TRADE_RETCODE_DONE, order=12345, deal=67890, comment="done")


class _FakeConnectionManager:
    def __init__(self) -> None:
        self.mt5 = _FakeMT5()


class _AllowedVerifier:
    def __init__(self) -> None:
        self.connection_manager = _FakeConnectionManager()

    def verify_demo_account(self):
        from backend.demo_execution.demo_execution_models import MT5DemoAccountStatus

        return MT5DemoAccountStatus(
            terminal_available=True,
            account_connected=True,
            account_login=123456,
            broker_server="Demo-Server",
            account_trade_mode="DEMO",
            is_demo_account=True,
            demo_execution_allowed=True,
            simulation_only=True,
            live_execution_enabled=False,
        )


def _service_with_items(*items):
    from backend.demo_execution.demo_execution_service import DemoExecutionService
    from backend.execution_queue.execution_queue_service import ExecutionQueueService

    queue_service = ExecutionQueueService()
    for item in items:
        queue_service.queue_manager.store.add_item(item)
    return DemoExecutionService(execution_queue_service=queue_service, account_verifier=_AllowedVerifier())


def verify_routes() -> bool:
    try:
        from backend.main import app

        routes = {route.path for route in app.routes}
        expected = {
            "/demo-execution/execute-latest-eligible",
            "/demo-execution/eligible-queue-items",
            "/demo-execution/audit-events",
            "/demo-execution/status",
            "/demo-execution/queue/{queue_id}/execute-demo",
        }
        return show("Day 2 demo execution routes registered", expected <= routes)
    except Exception as exc:
        return show("Day 2 demo execution routes registered", False, str(exc))


def verify_eligible_detection() -> bool:
    try:
        service = _service_with_items(
            _queue_item("EURUSD", 0.01, "BUY"),
            _queue_item("XAUUSD", 0.01, "BUY"),
            _queue_item("NIFTY50", 0.01, "BUY"),
            _queue_item("EURUSD", 0.02, "BUY"),
        )
        eligible = service.get_eligible_queue_items()
        passed = len(eligible) == 1 and eligible[0].intent.canonical_symbol == "EURUSD" and eligible[0].intent.allocated_lot == 0.01
        return show("Eligible queue detection includes EURUSD and excludes XAUUSD/NIFTY50/large lots", passed)
    except Exception as exc:
        return show("Eligible queue detection includes EURUSD and excludes XAUUSD/NIFTY50/large lots", False, str(exc))


def verify_latest_duplicate_lifecycle_and_audit() -> bool:
    try:
        item = _queue_item("EURUSD", 0.01, "BUY")
        service = _service_with_items(item)
        first = service.execute_latest_eligible(
            {
                "confirm_demo_execution": True,
                "requested_by": "phase5-day2-test",
                "reason": "Controlled latest eligible demo execution test.",
            }
        )
        duplicate = service.execute_queue_item_demo(
            item.queue_id,
            {
                "confirm_demo_execution": True,
                "requested_by": "phase5-day2-test",
                "reason": "Duplicate execution should be blocked.",
            },
        )
        events = service.get_audit_events(100)
        event_types = {event.event_type for event in events}
        lifecycle = service.execution_queue_service.lifecycle_service.tracker.get_lifecycle(item.queue_id)
        states = [entry.get("state") for entry in lifecycle.history]
        passed = (
            first.status == "DEMO_FILLED"
            and first.simulation_only is True
            and first.live_execution_enabled is False
            and first.broker_execution_enabled is False
            and duplicate.status == "BLOCKED"
            and any("already" in reason.lower() for reason in duplicate.rejection_reasons)
            and service.result_store.has_queue_execution(item.queue_id)
            and {"DEMO_EXECUTION_REQUESTED", "DEMO_ORDER_SENT", "DEMO_EXECUTION_FILLED", "DEMO_EXECUTION_BLOCKED"} <= event_types
            and "VALIDATED" in states
            and "DEMO_ORDER_SENT" in states
            and "DEMO_FILLED" in states
        )
        return show("Latest eligible execution, duplicate protection, lifecycle, and audit events work", passed)
    except Exception as exc:
        return show("Latest eligible execution, duplicate protection, lifecycle, and audit events work", False, str(exc))


def verify_confirm_false_blocked() -> bool:
    try:
        item = _queue_item("EURUSD", 0.01, "SELL")
        service = _service_with_items(item)
        result = service.execute_queue_item_demo(
            item.queue_id,
            {
                "confirm_demo_execution": False,
                "requested_by": "phase5-day2-test",
                "reason": "Missing confirmation should block.",
            },
        )
        passed = (
            result.status == "BLOCKED"
            and result.simulation_only is True
            and result.live_execution_enabled is False
            and result.broker_execution_enabled is False
            and any("confirm_demo_execution" in reason for reason in result.rejection_reasons)
            and len(service.list_results()) == 1
        )
        return show("confirm_demo_execution=false is blocked and stored safely", passed)
    except Exception as exc:
        return show("confirm_demo_execution=false is blocked and stored safely", False, str(exc))


def verify_enqueue_preview_to_eligible_route() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        payload = {
            "signal_id": "demo-flow-001-route-test",
            "canonical_symbol": "EURUSD",
            "action": "BUY",
            "allocation_mode": "EQUAL",
            "total_lot": 0.01,
        }
        enqueued = client.post("/execution-queue/enqueue-preview", json=payload)
        enqueued_items = enqueued.json()
        eligible = client.get("/demo-execution/eligible-queue-items").json()
        enqueued_ids = {item.get("queue_id") for item in enqueued_items}
        eligible_ids = {item.get("queue_id") for item in eligible}
        matching_items = [item for item in eligible if item.get("queue_id") in enqueued_ids]
        passed = (
            enqueued.status_code == 200
            and len(enqueued_items) >= 1
            and len(matching_items) >= 1
            and enqueued_ids <= eligible_ids
            and matching_items[0].get("readiness") == "READY_FOR_DEMO_QUEUE"
            and matching_items[0].get("intent", {}).get("canonical_symbol") == "EURUSD"
            and matching_items[0].get("intent", {}).get("action") == "BUY"
            and matching_items[0].get("intent", {}).get("order_type") == "MARKET"
            and matching_items[0].get("intent", {}).get("allocated_lot") <= 0.01
        )
        return show("enqueue-preview stores shared EURUSD queue item visible to eligible endpoint", passed)
    except Exception as exc:
        return show("enqueue-preview stores shared EURUSD queue item visible to eligible endpoint", False, str(exc))


def verify_api_outputs_json_safe() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        eligible = client.get("/demo-execution/eligible-queue-items")
        audit = client.get("/demo-execution/audit-events")
        latest = client.post(
            "/demo-execution/execute-latest-eligible",
            json={
                "confirm_demo_execution": False,
                "requested_by": "phase5-day2-test",
                "reason": "Route JSON safety check.",
            },
        )
        passed = (
            eligible.status_code == 200
            and audit.status_code == 200
            and latest.status_code == 200
            and latest.json().get("simulation_only") is True
            and latest.json().get("live_execution_enabled") is False
            and latest.json().get("broker_execution_enabled") is False
        )
        return show("Day 2 API outputs are JSON-safe and keep safety flags", passed)
    except Exception as exc:
        return show("Day 2 API outputs are JSON-safe and keep safety flags", False, str(exc))


def verify_order_send_isolated() -> bool:
    token = "mt5." + "order_send"
    matches = []
    for path in (PROJECT_ROOT / "backend").rglob("*.py"):
        if path.is_file() and token in path.read_text(encoding="utf-8", errors="ignore"):
            matches.append(path.relative_to(PROJECT_ROOT).as_posix())
    passed = matches == ["backend/demo_execution/mt5_demo_executor.py"]
    return show("MT5 order submission remains isolated to guarded demo executor", passed, ", ".join(matches))


def main() -> int:
    print("Phase 5 Day 2 Controlled MT5 Demo Order Flow Verification")
    print("=" * 65)
    checks = [
        verify_routes(),
        verify_eligible_detection(),
        verify_latest_duplicate_lifecycle_and_audit(),
        verify_confirm_false_blocked(),
        verify_enqueue_preview_to_eligible_route(),
        verify_api_outputs_json_safe(),
        verify_order_send_isolated(),
    ]
    print("=" * 65)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
