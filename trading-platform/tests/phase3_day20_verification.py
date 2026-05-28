import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


PHASE3_MODULES = {
    "replay",
    "replay_analytics",
    "replay_calibration",
    "replay_comparison",
    "client_symbols",
    "broker_compatibility",
    "mt5_demo_readiness",
    "broker_observation",
    "broker_feed_quality",
    "canonical_feed",
    "candle_feed",
    "tradingview_webhooks",
    "webhook_orchestration",
    "webhook_security",
    "account_routing",
    "account_allocation",
    "execution_queue",
    "execution_lifecycle",
    "monitoring_alerting",
}


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def verify_files_and_routes() -> bool:
    files = [
        "backend/phase3_readiness/__init__.py",
        "backend/phase3_readiness/phase3_readiness_models.py",
        "backend/phase3_readiness/phase3_module_registry.py",
        "backend/phase3_readiness/phase3_route_auditor.py",
        "backend/phase3_readiness/phase3_pipeline_validator.py",
        "backend/phase3_readiness/phase3_safety_auditor.py",
        "backend/phase3_readiness/phase3_client_readiness_report.py",
        "backend/phase3_readiness/phase3_readiness_service.py",
        "backend/api/phase3_readiness_routes.py",
        "docs/phase-3-completion-report.md",
        "docs/client-mvp-readiness-summary.md",
    ]
    files_ok = all((PROJECT_ROOT / path).is_file() for path in files)
    try:
        from backend.main import app

        routes = {route.path for route in app.routes}
        expected = {
            "/phase3/status",
            "/phase3/modules",
            "/phase3/routes",
            "/phase3/pipeline",
            "/phase3/safety-audit",
            "/phase3/client-readiness",
            "/monitoring/status",
        }
        routes_ok = expected <= routes
    except Exception:
        routes_ok = False
    return show("Phase 3 readiness files and routes exist", files_ok and routes_ok)


def verify_registry_and_route_auditor() -> bool:
    try:
        from backend.main import app
        from backend.phase3_readiness.phase3_module_registry import Phase3ModuleRegistry
        from backend.phase3_readiness.phase3_route_auditor import Phase3RouteAuditor

        registry = Phase3ModuleRegistry()
        modules = registry.list_modules({route.path for route in app.routes})
        module_names = {module.module_name for module in modules}
        audit = Phase3RouteAuditor(registry).audit_routes(app)
        passed = (
            PHASE3_MODULES <= module_names
            and audit["route_available"] is True
            and audit["missing_routes"] == []
            and audit["simulation_only"] is True
            and audit["live_execution_enabled"] is False
        )
        return show("Module registry and route auditor verify Phase 3 routes", passed)
    except Exception as exc:
        return show("Module registry and route auditor verify Phase 3 routes", False, str(exc))


def verify_pipeline_safety_and_client_report() -> bool:
    try:
        from backend.phase3_readiness.phase3_client_readiness_report import (
            Phase3ClientReadinessReportBuilder,
        )
        from backend.phase3_readiness.phase3_pipeline_validator import Phase3PipelineValidator
        from backend.phase3_readiness.phase3_safety_auditor import Phase3SafetyAuditor

        pipeline = Phase3PipelineValidator().validate_pipeline()
        safety = Phase3SafetyAuditor().run_safety_audit()
        client_report = Phase3ClientReadinessReportBuilder().build_report()
        json.dumps(pipeline.model_dump(mode="json"))
        json.dumps(safety.model_dump(mode="json"))
        json.dumps(client_report, default=str)
        passed = (
            pipeline.pipeline_status == "READY"
            and pipeline.webhook_ready is True
            and pipeline.routing_ready is True
            and pipeline.allocation_ready is True
            and pipeline.execution_queue_ready is True
            and pipeline.simulation_lifecycle_ready is True
            and pipeline.monitoring_ready is True
            and pipeline.simulation_only is True
            and pipeline.live_execution_enabled is False
            and safety.safety_status == "PASSED"
            and safety.no_order_send_detected is True
            and safety.live_execution_disabled is True
            and safety.broker_execution_disabled is True
            and "EURUSD" in client_report["supported_markets"]
            and "XAUUSD" in client_report["supported_markets"]
            and "NIFTY50" in client_report["supported_markets"]
            and "STARTRADER" in client_report["supported_brokers"]
            and "FXPRO" in client_report["supported_brokers"]
            and "VANTAGE" in client_report["supported_brokers"]
        )
        return show("Pipeline validator, safety auditor, and client report work", passed)
    except Exception as exc:
        return show("Pipeline validator, safety auditor, and client report work", False, str(exc))


def verify_api_outputs() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        endpoints = [
            "/phase3/status",
            "/phase3/modules",
            "/phase3/routes",
            "/phase3/pipeline",
            "/phase3/safety-audit",
            "/phase3/client-readiness",
            "/monitoring/status",
        ]
        responses = [client.get(endpoint) for endpoint in endpoints]
        payloads = [response.json() for response in responses]
        json.dumps(payloads, default=str)
        status = payloads[0]
        safety = payloads[4]
        passed = (
            all(response.status_code == 200 for response in responses)
            and status["overall_status"] == "READY"
            and status["simulation_only"] is True
            and status["live_execution_enabled"] is False
            and safety["safety_status"] == "PASSED"
            and safety["no_order_send_detected"] is True
        )
        return show("Phase 3 APIs are JSON-safe and ready", passed)
    except Exception as exc:
        return show("Phase 3 APIs are JSON-safe and ready", False, str(exc))


def main() -> int:
    print("Phase 3 Day 20 Integration Hardening Verification")
    print("=" * 58)
    checks = [
        verify_files_and_routes(),
        verify_registry_and_route_auditor(),
        verify_pipeline_safety_and_client_report(),
        verify_api_outputs(),
    ]
    print("=" * 58)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
