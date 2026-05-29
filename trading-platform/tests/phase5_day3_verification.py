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
        "backend/multi_account_execution/__init__.py",
        "backend/multi_account_execution/multi_account_models.py",
        "backend/multi_account_execution/account_execution_planner.py",
        "backend/multi_account_execution/multi_account_execution_guard.py",
        "backend/multi_account_execution/multi_account_demo_executor.py",
        "backend/multi_account_execution/multi_account_result_store.py",
        "backend/multi_account_execution/multi_account_execution_service.py",
        "backend/api/multi_account_execution_routes.py",
        "docs/phase-5-day-3-progress.md",
    ]
    return show("Multi-account execution package, router, and docs exist", all((PROJECT_ROOT / path).is_file() for path in files))


def verify_routes() -> bool:
    try:
        from backend.main import app

        routes = {route.path for route in app.routes}
        expected = {
            "/multi-account-execution/status",
            "/multi-account-execution/results",
            "/multi-account-execution/results/{batch_id}",
            "/multi-account-execution/preview-plans",
            "/multi-account-execution/execute-demo-batch",
            "/demo-execution/status",
            "/demo-execution/eligible-queue-items",
        }
        return show("Multi-account routes and Day 1/2 demo routes registered", expected <= routes)
    except Exception as exc:
        return show("Multi-account routes and Day 1/2 demo routes registered", False, str(exc))


def verify_planner_rules() -> bool:
    try:
        from backend.multi_account_execution.account_execution_planner import AccountExecutionPlanner

        planner = AccountExecutionPlanner()
        eurusd = planner.build_plans({"signal_id": "multi-demo-001", "canonical_symbol": "EURUSD", "action": "BUY", "total_lot": 0.03})
        xau = planner.build_plans({"signal_id": "multi-demo-xau", "canonical_symbol": "XAUUSD", "action": "BUY", "total_lot": 0.03})
        nifty = planner.build_plans({"signal_id": "multi-demo-nifty", "canonical_symbol": "NIFTY50", "action": "BUY", "total_lot": 0.03})
        passed = (
            len(eurusd) == 3
            and all(plan.eligible for plan in eurusd)
            and {plan.account_id for plan in eurusd} == {"STARTRADER_DEMO_1", "FXPRO_DEMO_1", "VANTAGE_DEMO_1"}
            and all(plan.canonical_symbol == "EURUSD" for plan in eurusd)
            and all(plan.lot <= 0.01 for plan in eurusd)
            and len(xau) == 3
            and all(not plan.eligible for plan in xau)
            and all(any("EURUSD" in reason for reason in plan.rejection_reasons) for plan in xau)
            and len(nifty) == 3
            and all(not plan.eligible for plan in nifty)
        )
        return show("Planner creates 3 EURUSD plans and blocks XAUUSD/NIFTY50", passed)
    except Exception as exc:
        return show("Planner creates 3 EURUSD plans and blocks XAUUSD/NIFTY50", False, str(exc))


def verify_guard_blocks_large_lot() -> bool:
    try:
        from backend.multi_account_execution.multi_account_execution_guard import MultiAccountExecutionGuard
        from backend.multi_account_execution.multi_account_models import AccountDemoExecutionPlan

        plan = AccountDemoExecutionPlan(
            signal_id="large-lot",
            account_id="STARTRADER_DEMO_1",
            broker_id="STARTRADER",
            canonical_symbol="EURUSD",
            broker_symbol="EURUSD",
            action="BUY",
            lot=0.02,
            order_type="MARKET",
            eligible=True,
        )
        allowed, reasons = MultiAccountExecutionGuard().validate_plan(plan)
        passed = allowed is False and any("<= 0.01" in reason for reason in reasons)
        return show("Multi-account guard blocks per-account lot greater than 0.01", passed)
    except Exception as exc:
        return show("Multi-account guard blocks per-account lot greater than 0.01", False, str(exc))


def verify_execution_store_duplicates_and_audit() -> bool:
    try:
        from backend.multi_account_execution.multi_account_execution_service import MultiAccountExecutionService

        service = MultiAccountExecutionService()
        payload = {
            "signal_id": "multi-demo-duplicate",
            "canonical_symbol": "EURUSD",
            "action": "BUY",
            "total_lot": 0.03,
            "confirm_demo_execution": False,
            "requested_by": "phase5-day3-test",
            "reason": "Verification batch.",
        }
        first = service.execute_demo_batch(payload)
        second = service.execute_demo_batch(payload)
        events = service.get_audit_events(100)
        passed = (
            first.total_targets == 3
            and len(first.account_results) == 3
            and first.simulation_only is True
            and first.live_execution_enabled is False
            and first.broker_execution_enabled is False
            and service.get_result(first.batch_id) is not None
            and len(service.list_results()) == 2
            and all(result.status == "SKIPPED_DUPLICATE" for result in second.account_results)
            and len(events) >= 3
        )
        return show("Execution batches store results, prevent duplicate per-account attempts, and audit actions", passed)
    except Exception as exc:
        return show("Execution batches store results, prevent duplicate per-account attempts, and audit actions", False, str(exc))


def verify_api_json_safe() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        status = client.get("/multi-account-execution/status")
        preview = client.post(
            "/multi-account-execution/preview-plans",
            json={"signal_id": "api-preview", "canonical_symbol": "EURUSD", "action": "SELL", "total_lot": 0.03},
        )
        xau = client.post(
            "/multi-account-execution/preview-plans",
            json={"signal_id": "api-xau", "canonical_symbol": "XAUUSD", "action": "BUY", "total_lot": 0.03},
        )
        result = client.post(
            "/multi-account-execution/execute-demo-batch",
            json={"signal_id": "api-batch", "canonical_symbol": "EURUSD", "action": "BUY", "total_lot": 0.03, "confirm_demo_execution": False},
        )
        status_json = status.json()
        result_json = result.json()
        passed = (
            status.status_code == 200
            and preview.status_code == 200
            and xau.status_code == 200
            and result.status_code == 200
            and len(preview.json()) == 3
            and all(plan.get("eligible") is True for plan in preview.json())
            and all(plan.get("eligible") is False for plan in xau.json())
            and status_json.get("simulation_only") is True
            and status_json.get("live_execution_enabled") is False
            and status_json.get("broker_execution_enabled") is False
            and result_json.get("simulation_only") is True
            and result_json.get("live_execution_enabled") is False
            and result_json.get("broker_execution_enabled") is False
        )
        return show("Multi-account API routes are JSON-safe and preserve safety flags", passed)
    except Exception as exc:
        return show("Multi-account API routes are JSON-safe and preserve safety flags", False, str(exc))


def verify_order_send_isolated() -> bool:
    token = "mt5." + "order_send"
    matches = []
    for path in (PROJECT_ROOT / "backend").rglob("*.py"):
        if path.is_file() and token in path.read_text(encoding="utf-8", errors="ignore"):
            matches.append(path.relative_to(PROJECT_ROOT).as_posix())
    passed = matches == ["backend/demo_execution/mt5_demo_executor.py"]
    return show("MT5 order submission remains isolated to guarded demo executor", passed, ", ".join(matches))


def main() -> int:
    print("Phase 5 Day 3 Multi-Account MT5 Demo Routing Verification")
    print("=" * 66)
    checks = [
        verify_files(),
        verify_routes(),
        verify_planner_rules(),
        verify_guard_blocks_large_lot(),
        verify_execution_store_duplicates_and_audit(),
        verify_api_json_safe(),
        verify_order_send_isolated(),
    ]
    print("=" * 66)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
