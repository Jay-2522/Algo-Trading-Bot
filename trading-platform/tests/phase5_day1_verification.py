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
        "backend/demo_execution/__init__.py",
        "backend/demo_execution/demo_execution_models.py",
        "backend/demo_execution/mt5_demo_account_verifier.py",
        "backend/demo_execution/mt5_demo_order_builder.py",
        "backend/demo_execution/mt5_demo_execution_guard.py",
        "backend/demo_execution/mt5_demo_executor.py",
        "backend/demo_execution/demo_execution_result_store.py",
        "backend/demo_execution/demo_execution_service.py",
        "backend/api/demo_execution_routes.py",
        "docs/phase-5-day-1-progress.md",
    ]
    return show("Demo execution package, router, and documentation exist", all((PROJECT_ROOT / path).is_file() for path in files))


def verify_routes() -> bool:
    try:
        from backend.main import app

        routes = {route.path for route in app.routes}
        expected = {
            "/demo-execution/status",
            "/demo-execution/account-status",
            "/demo-execution/results",
            "/demo-execution/results/{execution_id}",
            "/demo-execution/queue/{queue_id}/execute-demo",
            "/execution-queue/status",
        }
        return show("Demo execution routes and previous queue routes registered", expected <= routes)
    except Exception as exc:
        return show("Demo execution routes and previous queue routes registered", False, str(exc))


def verify_verifier_and_builder() -> bool:
    try:
        from backend.broker_integrations.mt5.mt5_connection_manager import MT5ConnectionManager
        from backend.demo_execution.mt5_demo_account_verifier import MT5DemoAccountVerifier
        from backend.demo_execution.mt5_demo_order_builder import MT5DemoOrderBuilder
        from backend.execution_queue.execution_queue_models import ExecutionIntent

        status = MT5DemoAccountVerifier(MT5ConnectionManager(mt5_module=None)).verify_demo_account()
        intent = ExecutionIntent(
            signal_id="verify-builder",
            account_id="STARTRADER_DEMO_1",
            broker_id="STARTRADER",
            canonical_symbol="EURUSD",
            broker_symbol="EURUSD",
            action="BUY",
            allocated_lot=0.01,
            order_type="MARKET",
            requested_price=1.085,
        )
        order = MT5DemoOrderBuilder().build_market_order(intent)
        passed = (
            status.demo_execution_allowed is False
            and status.simulation_only is True
            and status.live_execution_enabled is False
            and order["symbol"] == "EURUSD"
            and order["volume"] == 0.01
            and order["comment"] == "AI_BOT_DEMO_TEST"
        )
        return show("Account verifier fails safely and EURUSD market order builder works", passed)
    except Exception as exc:
        return show("Account verifier fails safely and EURUSD market order builder works", False, str(exc))


def _queue_item(symbol: str = "EURUSD", lot: float = 0.01, action: str = "BUY"):
    from backend.execution_queue.execution_queue_models import ExecutionIntent, ExecutionQueueItem

    intent = ExecutionIntent(
        signal_id=f"guard-{symbol}-{lot}",
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


class _AllowedVerifier:
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
            live_execution_enabled=False,
        )


def verify_guard_rules() -> bool:
    try:
        from backend.demo_execution.demo_execution_models import DemoExecutionRequest
        from backend.demo_execution.mt5_demo_execution_guard import MT5DemoExecutionGuard

        guard = MT5DemoExecutionGuard(account_verifier=_AllowedVerifier())
        no_confirm = guard.validate_demo_execution(
            _queue_item(),
            DemoExecutionRequest(queue_id="q1", confirm_demo_execution=False),
        )[1]
        big_lot = guard.validate_demo_execution(
            _queue_item(lot=0.02),
            DemoExecutionRequest(queue_id="q2", confirm_demo_execution=True),
        )[1]
        xau = guard.validate_demo_execution(
            _queue_item(symbol="XAUUSD"),
            DemoExecutionRequest(queue_id="q3", confirm_demo_execution=True),
        )[1]
        nifty = guard.validate_demo_execution(
            _queue_item(symbol="NIFTY50"),
            DemoExecutionRequest(queue_id="q4", confirm_demo_execution=True),
        )[1]
        passed = (
            any("confirm_demo_execution" in reason for reason in no_confirm)
            and any("<= 0.01" in reason for reason in big_lot)
            and any("EURUSD" in reason for reason in xau)
            and any("EURUSD" in reason for reason in nifty)
        )
        return show("Execution guard blocks missing confirmation, large lots, XAUUSD, and NIFTY50", passed)
    except Exception as exc:
        return show("Execution guard blocks missing confirmation, large lots, XAUUSD, and NIFTY50", False, str(exc))


def verify_store_and_routes_json() -> bool:
    try:
        from backend.demo_execution.demo_execution_models import DemoExecutionResult
        from backend.demo_execution.demo_execution_result_store import DemoExecutionResultStore
        from backend.main import app

        store = DemoExecutionResultStore()
        stored = store.store_result(DemoExecutionResult(queue_id="q-store", status="BLOCKED"))
        client = TestClient(app)
        status = client.get("/demo-execution/status")
        account = client.get("/demo-execution/account-status")
        results = client.get("/demo-execution/results")
        blocked = client.post(
            "/demo-execution/queue/q-missing/execute-demo",
            json={
                "queue_id": "q-missing",
                "confirm_demo_execution": False,
                "requested_by": "phase5-verification",
                "reason": "Verify blocked demo execution remains simulation-only.",
            },
        )
        blocked_json = blocked.json()
        passed = (
            store.get_result(stored.execution_id) is not None
            and store.get_result(stored.execution_id).simulation_only is True
            and stored.simulation_only is True
            and len(store.list_results()) == 1
            and status.status_code == 200
            and account.status_code == 200
            and results.status_code == 200
            and blocked.status_code == 200
            and status.json().get("simulation_only") is True
            and status.json().get("live_execution_enabled") is False
            and status.json().get("broker_execution_enabled") is False
            and account.json().get("simulation_only") is True
            and account.json().get("live_execution_enabled") is False
            and blocked_json.get("simulation_only") is True
            and blocked_json.get("live_execution_enabled") is False
        )
        return show("Result store works and demo execution APIs return JSON-safe status", passed)
    except Exception as exc:
        return show("Result store works and demo execution APIs return JSON-safe status", False, str(exc))


def verify_order_send_isolated() -> bool:
    token = "mt5." + "order_send"
    matches = []
    for path in (PROJECT_ROOT / "backend").rglob("*.py"):
        if path.is_file() and token in path.read_text(encoding="utf-8", errors="ignore"):
            matches.append(path.relative_to(PROJECT_ROOT).as_posix())
    passed = matches == ["backend/demo_execution/mt5_demo_executor.py"]
    return show("MT5 order submission appears only in guarded demo executor", passed, ", ".join(matches))


def main() -> int:
    print("Phase 5 Day 1 MT5 Demo Execution Bridge Verification")
    print("=" * 58)
    checks = [
        verify_files(),
        verify_routes(),
        verify_verifier_and_builder(),
        verify_guard_rules(),
        verify_store_and_routes_json(),
        verify_order_send_isolated(),
    ]
    print("=" * 58)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
