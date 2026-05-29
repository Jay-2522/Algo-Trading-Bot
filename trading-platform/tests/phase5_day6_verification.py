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
        "backend/execution_risk/__init__.py",
        "backend/execution_risk/execution_risk_models.py",
        "backend/execution_risk/execution_risk_policy.py",
        "backend/execution_risk/execution_risk_evaluator.py",
        "backend/execution_risk/execution_risk_audit_store.py",
        "backend/execution_risk/execution_risk_service.py",
        "backend/api/execution_risk_routes.py",
        "docs/phase-5-day-6-progress.md",
    ]
    return show("Execution risk package, router, and docs exist", all((PROJECT_ROOT / path).is_file() for path in files))


def verify_routes() -> bool:
    try:
        from backend.main import app

        routes = {route.path for route in app.routes}
        expected = {
            "/execution-risk/status",
            "/execution-risk/policy",
            "/execution-risk/evaluate",
            "/execution-risk/decisions",
            "/execution-risk/audit-events",
            "/demo-execution/status",
            "/multi-account-execution/status",
            "/trade-copier/status",
            "/execution-confirmation/status",
        }
        return show("Execution risk routes and Day 1-Day 5 routes registered", expected <= routes)
    except Exception as exc:
        return show("Execution risk routes and Day 1-Day 5 routes registered", False, str(exc))


def verify_policy() -> bool:
    try:
        from backend.execution_risk.execution_risk_policy import ExecutionRiskPolicyProvider

        policy = ExecutionRiskPolicyProvider().get_policy()
        passed = (
            policy.allowed_symbols == ["EURUSD"]
            and "XAUUSD" in policy.blocked_symbols
            and "NIFTY50" in policy.blocked_symbols
            and policy.max_lot_per_account == 0.01
            and policy.max_target_accounts == 3
            and policy.max_daily_demo_attempts == 20
            and policy.simulation_only is True
            and policy.live_execution_enabled is False
            and policy.broker_execution_enabled is False
        )
        return show("Policy allows EURUSD and blocks XAUUSD/NIFTY50 with safety flags", passed)
    except Exception as exc:
        return show("Policy allows EURUSD and blocks XAUUSD/NIFTY50 with safety flags", False, str(exc))


def base_payload(**overrides):
    payload = {
        "request_id": "risk-test-001",
        "canonical_symbol": "EURUSD",
        "action": "BUY",
        "account_id": "STARTRADER_DEMO_1",
        "broker_id": "STARTRADER",
        "lot": 0.01,
        "confirm_demo_execution": True,
    }
    payload.update(overrides)
    return payload


def verify_evaluator() -> bool:
    try:
        from backend.execution_risk.execution_risk_evaluator import ExecutionRiskEvaluator

        evaluator = ExecutionRiskEvaluator()
        allowed = evaluator.evaluate_single_account_request(base_payload())
        over_lot = evaluator.evaluate_single_account_request(base_payload(request_id="risk-test-003", lot=0.02))
        missing_confirmation = evaluator.evaluate_single_account_request(base_payload(request_id="risk-missing-confirm", confirm_demo_execution=False))
        xau = evaluator.evaluate_single_account_request(base_payload(request_id="risk-test-002", canonical_symbol="XAUUSD"))
        nifty = evaluator.evaluate_single_account_request(base_payload(request_id="risk-nifty", canonical_symbol="NIFTY50"))
        multi = evaluator.evaluate_multi_account_request(base_payload(request_id="risk-multi", target_account_count=4))
        passed = (
            allowed.approved is True
            and allowed.risk_level == "LOW"
            and over_lot.approved is False
            and over_lot.risk_level == "BLOCKED"
            and any("<= 0.01" in reason for reason in over_lot.rejection_reasons)
            and missing_confirmation.approved is False
            and any("confirm_demo_execution" in reason for reason in missing_confirmation.rejection_reasons)
            and xau.approved is False
            and xau.risk_level == "BLOCKED"
            and nifty.approved is False
            and nifty.risk_level == "BLOCKED"
            and multi.approved is False
            and any("<= 3" in reason for reason in multi.rejection_reasons)
            and allowed.simulation_only is True
            and allowed.live_execution_enabled is False
            and allowed.broker_execution_enabled is False
        )
        return show("Evaluator approves safe EURUSD and blocks over-lot, missing confirmation, XAUUSD, NIFTY50, and too many targets", passed)
    except Exception as exc:
        return show("Evaluator approves safe EURUSD and blocks over-lot, missing confirmation, XAUUSD, NIFTY50, and too many targets", False, str(exc))


def verify_audit_store_and_api() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        status = client.get("/execution-risk/status")
        policy = client.get("/execution-risk/policy")
        allowed = client.post("/execution-risk/evaluate", json=base_payload(request_id="risk-api-allowed"))
        blocked = client.post("/execution-risk/evaluate", json=base_payload(request_id="risk-api-xau", canonical_symbol="XAUUSD"))
        decisions = client.get("/execution-risk/decisions")
        events = client.get("/execution-risk/audit-events")
        passed = (
            status.status_code == 200
            and policy.status_code == 200
            and allowed.status_code == 200
            and blocked.status_code == 200
            and decisions.status_code == 200
            and events.status_code == 200
            and allowed.json().get("approved") is True
            and allowed.json().get("simulation_only") is True
            and allowed.json().get("live_execution_enabled") is False
            and allowed.json().get("broker_execution_enabled") is False
            and blocked.json().get("approved") is False
            and len(decisions.json()) >= 2
            and len(events.json()) >= 2
        )
        return show("Execution risk APIs record decisions and audit events with safety flags", passed)
    except Exception as exc:
        return show("Execution risk APIs record decisions and audit events with safety flags", False, str(exc))


def verify_integration_points() -> bool:
    files = [
        PROJECT_ROOT / "backend/demo_execution/mt5_demo_execution_guard.py",
        PROJECT_ROOT / "backend/multi_account_execution/multi_account_execution_guard.py",
        PROJECT_ROOT / "backend/trade_copier/trade_copier_service.py",
    ]
    text = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in files)
    passed = (
        text.count("ExecutionRiskEvaluator") >= 3
        and "evaluate_single_account_request" in text
        and "evaluate_copy_request" in text
    )
    return show("Demo execution, multi-account, and trade copier integration points call risk evaluator", passed)


def verify_module_registry() -> bool:
    try:
        from backend.system_health.module_registry import get_module_registry

        modules = get_module_registry()
        passed = any(module["name"] == "execution_risk_enforcement" and module["route"] == "/execution-risk/status" for module in modules)
        return show("Execution risk appears in module registry", passed)
    except Exception as exc:
        return show("Execution risk appears in module registry", False, str(exc))


def verify_order_send_isolated() -> bool:
    token = "mt5." + "order_send"
    matches = []
    for path in (PROJECT_ROOT / "backend").rglob("*.py"):
        if path.is_file() and token in path.read_text(encoding="utf-8", errors="ignore"):
            matches.append(path.relative_to(PROJECT_ROOT).as_posix())
    passed = matches == ["backend/demo_execution/mt5_demo_executor.py"]
    return show("MT5 order submission remains isolated to guarded demo executor", passed, ", ".join(matches))


def main() -> int:
    print("Phase 5 Day 6 Execution Risk Enforcement Verification")
    print("=" * 62)
    checks = [
        verify_files(),
        verify_routes(),
        verify_policy(),
        verify_evaluator(),
        verify_audit_store_and_api(),
        verify_integration_points(),
        verify_module_registry(),
        verify_order_send_isolated(),
    ]
    print("=" * 62)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
