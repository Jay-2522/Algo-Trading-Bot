import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def verify_phase3_modules_and_routes() -> bool:
    try:
        from backend.main import app
        from backend.phase3_readiness.phase3_module_registry import Phase3ModuleRegistry
        from backend.phase3_readiness.phase3_route_auditor import Phase3RouteAuditor

        routes = {route.path for route in app.routes}
        modules = Phase3ModuleRegistry().list_modules(routes)
        audit = Phase3RouteAuditor().audit_routes(app)
        passed = (
            len(modules) >= 19
            and all(module.simulation_only is True for module in modules)
            and all(module.live_execution_enabled is False for module in modules)
            and all(module.route_available for module in modules)
            and audit["route_available"] is True
            and audit["missing_routes"] == []
        )
        return show("All Phase 3 modules and critical routes are registered", passed)
    except Exception as exc:
        return show("All Phase 3 modules and critical routes are registered", False, str(exc))


def verify_phase3_service_outputs() -> bool:
    try:
        from backend.phase3_readiness.phase3_readiness_service import Phase3ReadinessService

        service = Phase3ReadinessService()
        status = service.get_status()
        modules = service.get_modules()
        routes = service.get_routes()
        pipeline = service.validate_pipeline()
        safety = service.run_safety_audit()
        client_report = service.get_client_readiness_report()
        json.dumps(
            {
                "status": status.model_dump(mode="json"),
                "modules": [module.model_dump(mode="json") for module in modules],
                "routes": routes,
                "pipeline": pipeline.model_dump(mode="json"),
                "safety": safety.model_dump(mode="json"),
                "client_report": client_report,
            },
            default=str,
        )
        passed = (
            status.overall_status == "READY"
            and status.simulation_only is True
            and status.live_execution_enabled is False
            and pipeline.pipeline_status == "READY"
            and safety.safety_status == "PASSED"
            and client_report["client_mvp_status"] == "BACKEND_READY_FOR_VPS_DASHBOARD_PREPARATION"
        )
        return show("Readiness service outputs are JSON-safe and ready", passed)
    except Exception as exc:
        return show("Readiness service outputs are JSON-safe and ready", False, str(exc))


def verify_api_contracts() -> bool:
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
            "/replay/status",
            "/brokers/status",
            "/brokers/candles/status",
            "/webhooks/status",
            "/webhooks/orchestration/status",
            "/webhooks/security/status",
            "/accounts/status",
            "/accounts/allocation/status",
            "/execution-queue/status",
            "/execution-queue/lifecycle/status",
            "/monitoring/status",
        ]
        responses = {endpoint: client.get(endpoint) for endpoint in endpoints}
        payloads = {endpoint: response.json() for endpoint, response in responses.items()}
        json.dumps(payloads, default=str)
        passed = (
            all(response.status_code == 200 for response in responses.values())
            and payloads["/phase3/status"]["overall_status"] == "READY"
            and payloads["/phase3/safety-audit"]["safety_status"] == "PASSED"
            and payloads["/phase3/pipeline"]["simulation_only"] is True
            and payloads["/phase3/pipeline"]["live_execution_enabled"] is False
        )
        return show("Critical Phase 3 API contracts respond safely", passed)
    except Exception as exc:
        return show("Critical Phase 3 API contracts respond safely", False, str(exc))


def verify_no_live_execution_patterns() -> bool:
    try:
        from backend.phase3_readiness.phase3_safety_auditor import Phase3SafetyAuditor

        safety = Phase3SafetyAuditor(PROJECT_ROOT).run_safety_audit()
        passed = (
            safety.no_order_send_detected is True
            and safety.live_execution_disabled is True
            and safety.broker_execution_disabled is True
            and safety.simulation_only_confirmed is True
            and safety.safety_status == "PASSED"
        )
        return show("No live execution patterns are detected", passed)
    except Exception as exc:
        return show("No live execution patterns are detected", False, str(exc))


def main() -> int:
    print("Phase 3 Full Verification")
    print("=" * 36)
    checks = [
        verify_phase3_modules_and_routes(),
        verify_phase3_service_outputs(),
        verify_api_contracts(),
        verify_no_live_execution_patterns(),
    ]
    print("=" * 36)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
