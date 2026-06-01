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
        "backend/deployment/runtime_models.py",
        "backend/deployment/runtime_manager.py",
        "backend/deployment/service_health_checker.py",
        "backend/deployment/runtime_audit_store.py",
        "scripts/runtime_status.ps1",
        "scripts/restart_backend.ps1",
        "scripts/restart_frontend.ps1",
        "scripts/restart_all.ps1",
        "scripts/vps_healthcheck.ps1",
        "docs/phase-10-day-4-progress.md",
        "docs/vps-runtime-guide.md",
        "docs/windows-vps-service-guide.md",
        "docs/linux-vps-service-guide.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    return show("Runtime models, managers, scripts, and docs exist", not missing, ", ".join(missing))


def verify_imports_and_models() -> bool:
    try:
        from backend.deployment.runtime_audit_store import RuntimeAuditStore
        from backend.deployment.runtime_manager import RuntimeManager
        from backend.deployment.runtime_models import RuntimeServiceStatus, VPSRuntimeStatus
        from backend.deployment.service_health_checker import ServiceHealthChecker

        model_ok = RuntimeServiceStatus.model_fields and VPSRuntimeStatus.model_fields
        imports_ok = all(item is not None for item in [RuntimeAuditStore, RuntimeManager, ServiceHealthChecker])
        return show("Runtime models, manager, service health checker, and audit store import", bool(model_ok and imports_ok))
    except Exception as exc:
        return show("Runtime models, manager, service health checker, and audit store import", False, str(exc))


def verify_routes_and_endpoints() -> bool:
    try:
        from backend.main import app

        route_methods = {route.path: set(getattr(route, "methods", set()) or set()) for route in app.routes}
        required = [
            "/deployment/runtime/status",
            "/deployment/runtime/backend",
            "/deployment/runtime/frontend",
            "/deployment/runtime/healthcheck",
            "/deployment/runtime/mt5-notes",
            "/deployment/runtime/audit-events",
        ]
        routes_ok = all("GET" in route_methods.get(route, set()) for route in required)
        client = TestClient(app)
        status = client.get("/deployment/runtime/status")
        backend = client.get("/deployment/runtime/backend")
        frontend = client.get("/deployment/runtime/frontend")
        healthcheck = client.get("/deployment/runtime/healthcheck")
        mt5_notes = client.get("/deployment/runtime/mt5-notes")
        audit = client.get("/deployment/runtime/audit-events")
        status_payload = status.json()
        mt5_payload = mt5_notes.json()
        passed = (
            routes_ok
            and status.status_code == 200
            and backend.status_code == 200
            and frontend.status_code == 200
            and healthcheck.status_code == 200
            and mt5_notes.status_code == 200
            and audit.status_code == 200
            and status_payload["simulation_only"] is True
            and status_payload["demo_execution"] is True
            and status_payload["live_execution_enabled"] is False
            and status_payload["broker_execution_enabled"] is False
            and mt5_payload["demo_account_required"] is True
            and mt5_payload["live_execution_enabled"] is False
            and isinstance(audit.json(), list)
        )
        return show("Runtime routes registered and endpoints work safely", passed)
    except Exception as exc:
        return show("Runtime routes registered and endpoints work safely", False, str(exc))


def verify_health_checker_handles_success_and_failure() -> bool:
    try:
        from backend.deployment.service_health_checker import ServiceHealthChecker

        checker = ServiceHealthChecker()
        backend_status = checker.check_backend()
        checker.BACKEND_URL = "http://127.0.0.1:1/unavailable"
        checker.FRONTEND_URL = "http://127.0.0.1:1/unavailable"
        backend_failure = checker.check_backend()
        frontend_failure = checker.check_frontend()
        passed = (
            backend_status.status in {"RUNNING", "STOPPED", "DEGRADED", "UNKNOWN"}
            and backend_failure.status in {"STOPPED", "UNKNOWN"}
            and frontend_failure.status in {"STOPPED", "UNKNOWN"}
            and backend_failure.running is False
            and frontend_failure.running is False
            and backend_failure.warnings
            and frontend_failure.warnings
        )
        return show("Backend and frontend health checks handle success/failure safely", passed)
    except Exception as exc:
        return show("Backend and frontend health checks handle success/failure safely", False, str(exc))


def verify_deployment_readiness_and_preserved_routes() -> bool:
    try:
        from backend.main import app
        from tests.regression_routes_verification import REQUIRED_GET_ROUTES, REQUIRED_WEBSOCKET_ROUTES

        client = TestClient(app)
        readiness = client.get("/deployment/readiness").json()
        registered_get_routes = {
            route.path for route in app.routes if hasattr(route, "methods") and "GET" in route.methods
        }
        registered_websockets = {
            route.path for route in app.routes if route.__class__.__name__ == "APIWebSocketRoute"
        }
        required = {
            "/deployment/status",
            "/deployment/runtime/status",
            "/monitoring/health",
            "/strategy-execution-bridge/operations/status",
        }
        missing = sorted((REQUIRED_GET_ROUTES | required) - registered_get_routes)
        missing_ws = sorted(REQUIRED_WEBSOCKET_ROUTES - registered_websockets)
        token = "mt5." + "order_send"
        matches = []
        for path in (PROJECT_ROOT / "backend").rglob("*.py"):
            if path.is_file() and token in path.read_text(encoding="utf-8", errors="ignore"):
                matches.append(path.relative_to(PROJECT_ROOT).as_posix())
        passed = (
            readiness["runtime_ready"] is True
            and readiness["service_management_ready"] is True
            and readiness["simulation_only"] is True
            and readiness["demo_execution"] is True
            and readiness["live_execution_enabled"] is False
            and readiness["broker_execution_enabled"] is False
            and not missing
            and not missing_ws
            and matches == ["backend/demo_execution/mt5_demo_executor.py"]
        )
        return show("Deployment readiness includes runtime/service management and preserves routes/safety", passed, ", ".join(missing + missing_ws + matches))
    except Exception as exc:
        return show("Deployment readiness includes runtime/service management and preserves routes/safety", False, str(exc))


def main() -> int:
    print("Phase 10 Day 4 VPS Runtime Verification")
    print("=" * 50)
    checks = [
        verify_files(),
        verify_imports_and_models(),
        verify_routes_and_endpoints(),
        verify_health_checker_handles_success_and_failure(),
        verify_deployment_readiness_and_preserved_routes(),
    ]
    print("=" * 50)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
