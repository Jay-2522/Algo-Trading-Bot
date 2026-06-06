import sys
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

ROUTES = {
    "/mt5-demo/demo-approval-workflow/status",
    "/mt5-demo/demo-approval-workflow/run",
    "/mt5-demo/demo-approval-workflow/latest",
    "/mt5-demo/demo-approval-workflow/history",
}

VALID_WORKFLOW = {
    "environment": "DEMO",
    "symbol": "EURUSD",
    "action": "BUY",
    "lot": 0.01,
    "entry_price": 1.12345,
    "stop_loss": 1.12,
    "take_profit": 1.13,
    "manual_confirmation": True,
    "acknowledge_no_live_trading": True,
    "acknowledge_demo_only": True,
    "acknowledge_no_order_placement_today": True,
}


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def walk(payload: Any):
    if isinstance(payload, dict):
        for key, value in payload.items():
            yield key, value
            yield from walk(value)
    elif isinstance(payload, list):
        for item in payload:
            yield from walk(item)


def safety_ok(payload: Any) -> bool:
    for key, value in walk(payload):
        if key in {"execution_allowed", "mt5_order_sent", "would_send_to_mt5", "live_execution_enabled", "broker_execution_enabled"} and value is True:
            return False
    return True


def install_read_only_environment_stubs() -> None:
    from backend.api import mt5_demo_routes

    mt5_demo_routes.service.get_status = lambda: {
        "status": "CONNECTED",
        "environment": "DEMO",
        "simulation_only": True,
        "live_execution_enabled": False,
        "broker_execution_enabled": False,
        "execution_allowed": False,
    }
    mt5_demo_routes.market_data_service.get_market_data_status = lambda: {
        "status": "READY",
        "simulation_only": True,
        "live_execution_enabled": False,
        "broker_execution_enabled": False,
        "execution_allowed": False,
    }
    mt5_demo_routes.market_data_service.get_symbol_spread = lambda symbol: {
        "symbol": symbol,
        "bid": 1.1234,
        "ask": 1.12345,
        "spread": 0.00005,
        "status": "OK",
        "simulation_only": True,
        "live_execution_enabled": False,
        "broker_execution_enabled": False,
        "execution_allowed": False,
    }
    mt5_demo_routes.historical_backfill_service.summarize_backfill = lambda symbol, timeframe: {
        "symbol": symbol,
        "timeframe": timeframe,
        "returned_count": 500,
        "validation": {"valid": True, "stale": False, "warnings": []},
        "status": "OK",
        "simulation_only": True,
        "live_execution_enabled": False,
        "broker_execution_enabled": False,
        "execution_allowed": False,
    }
    mt5_demo_routes.strategy_feed_adapter.build_strategy_feed = lambda symbol: {
        "symbol": symbol,
        "feed_ready": True,
        "status": "READY",
        "simulation_only": True,
        "live_execution_enabled": False,
        "broker_execution_enabled": False,
        "execution_allowed": False,
    }


def verify_workflow_routes_and_sequence() -> bool:
    try:
        from backend.main import app

        install_read_only_environment_stubs()
        client = TestClient(app)
        paths = {route.path for route in app.routes if hasattr(route, "methods")}
        missing = sorted(ROUTES - paths)
        status = client.get("/mt5-demo/demo-approval-workflow/status")
        invalid = client.post("/mt5-demo/demo-approval-workflow/run", json={"environment": "DEMO"})
        valid = client.post("/mt5-demo/demo-approval-workflow/run", json=VALID_WORKFLOW)
        latest = client.get("/mt5-demo/demo-approval-workflow/latest")
        history = client.get("/mt5-demo/demo-approval-workflow/history")
        valid_json = valid.json()
        final = valid_json.get("final_approval_result", {})
        missing_step_blockers = {
            "AUTHORIZATION_NOT_GRANTED",
            "DRY_RUN_NOT_VALIDATED",
            "PREFLIGHT_NOT_VALIDATED",
            "SIMULATOR_NOT_VALIDATED",
            "TEST_PLAN_NOT_GENERATED",
            "FINAL_APPROVAL_NOT_GRANTED",
        }
        passed = (
            not missing
            and all(response.status_code == 200 for response in [status, invalid, valid, latest, history])
            and invalid.json()["status"] == "BLOCKED"
            and len(invalid.json()["blockers"]) >= 1
            and valid_json["status"] in {"APPROVED_FOR_FUTURE_SINGLE_DEMO_ORDER_TEST", "BLOCKED"}
            and valid_json["authorization_result"]
            and valid_json["dry_run_result"]
            and valid_json["preflight_result"]
            and valid_json["simulator_result"]
            and valid_json["readiness_result"]
            and valid_json["test_plan_result"]
            and valid_json["final_approval_result"]
            and valid_json["authorization_result"].get("authorization_granted") is True
            and valid_json["dry_run_result"].get("validation_passed") is True
            and valid_json["preflight_result"].get("validation_passed") is True
            and valid_json["simulator_result"].get("simulation_passed") is True
            and isinstance(valid_json["readiness_result"].get("overall_score"), int)
            and valid_json["test_plan_result"].get("status") == "READY_FOR_FUTURE_DEMO_TESTING"
            and final.get("decision") in {
                "APPROVED_FOR_FUTURE_SINGLE_DEMO_ORDER_TEST",
                "NOT_APPROVED",
                "BLOCKED_BY_SAFETY",
                "BLOCKED_BY_MISSING_READINESS",
                "BLOCKED_BY_MISSING_MANUAL_CONFIRMATION",
            }
            and not (set(valid_json["blockers"]) & missing_step_blockers)
            and valid_json["execution_allowed"] is False
            and valid_json["mt5_order_sent"] is False
            and valid_json["would_send_to_mt5"] is False
            and valid_json["live_execution_enabled"] is False
            and valid_json["broker_execution_enabled"] is False
            and latest.json().get("workflow_id") == valid_json.get("workflow_id")
            and isinstance(history.json(), list)
            and len(history.json()) >= 1
            and safety_ok(valid_json)
        )
        return show("Consolidated workflow routes complete sequence safely", passed, ", ".join(missing + sorted(set(valid_json.get("blockers", [])) & missing_step_blockers)))
    except Exception as exc:
        return show("Consolidated workflow routes complete sequence safely", False, str(exc))


def verify_files() -> bool:
    files = [
        "backend/mt5_demo/demo_approval_workflow_service.py",
        "docs/phase16-missing-sequence-complete-workflow.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    return show("Workflow service and docs exist", not missing, ", ".join(missing))


def verify_no_order_send_added() -> bool:
    token = "mt5." + "order_send"
    allowed = [
        "backend/demo_execution/mt5_demo_executor.py",
        "backend/mt5_demo/guarded_demo_order_sender_service.py",
    ]
    matches = [
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in (PROJECT_ROOT / "backend").rglob("*.py")
        if token in path.read_text(encoding="utf-8", errors="ignore")
    ]
    return show("No unrestricted mt5 order execution path was added", sorted(matches) == allowed, ", ".join(matches))


def main() -> int:
    print("Phase 16 Missing Sequence Complete Workflow Verification")
    print("=" * 78)
    checks = [verify_files(), verify_workflow_routes_and_sequence(), verify_no_order_send_added()]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
