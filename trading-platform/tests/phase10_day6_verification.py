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
        "backend/deployment/backup_models.py",
        "backend/deployment/backup_readiness_service.py",
        "backend/deployment/recovery_runbook_service.py",
        "backend/api/backup_routes.py",
        "scripts/backup_status.ps1",
        "scripts/recovery_check.ps1",
        "docs/phase-10-day-6-progress.md",
        "docs/backup-strategy.md",
        "docs/recovery-runbook.md",
        "docs/deployment-rollback-guide.md",
        "docs/incident-response-guide.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    return show("Backup models, services, routes, scripts, and docs exist", not missing, ", ".join(missing))


def verify_service_status_and_score() -> bool:
    try:
        from backend.deployment.backup_models import BackupReadinessStatus
        from backend.deployment.backup_readiness_service import BackupReadinessService
        from backend.deployment.recovery_runbook_service import RecoveryRunbookService

        status = BackupReadinessService(PROJECT_ROOT).get_status()
        recovery = RecoveryRunbookService().get_full_recovery_plan()
        passed = (
            isinstance(status, BackupReadinessStatus)
            and status.backups_defined is True
            and status.rollback_defined is True
            and status.recovery_defined is True
            and status.incident_response_defined is True
            and status.recovery_score == 100
            and status.simulation_only is True
            and status.demo_execution is True
            and status.live_execution_enabled is False
            and status.broker_execution_enabled is False
            and recovery["simulation_only"] is True
            and recovery["live_execution_enabled"] is False
            and recovery["broker_execution_enabled"] is False
            and "mt5" in recovery
            and "backend" in recovery
            and "frontend" in recovery
        )
        return show("Recovery score and read-only runbook services work", passed)
    except Exception as exc:
        return show("Recovery score and read-only runbook services work", False, str(exc))


def verify_backup_routes() -> bool:
    try:
        from backend.main import app

        required = [
            "/backup/status",
            "/backup/strategy",
            "/backup/recovery",
            "/backup/rollback",
            "/backup/incident-response",
        ]
        route_methods = {route.path: set(getattr(route, "methods", set()) or set()) for route in app.routes}
        routes_ok = all("GET" in route_methods.get(route, set()) for route in required)
        client = TestClient(app)
        responses = {route: client.get(route) for route in required}
        status_payload = responses["/backup/status"].json()
        incident_payload = responses["/backup/incident-response"].json()
        passed = (
            routes_ok
            and all(response.status_code == 200 for response in responses.values())
            and status_payload["recovery_score"] == 100
            and status_payload["simulation_only"] is True
            and status_payload["live_execution_enabled"] is False
            and status_payload["broker_execution_enabled"] is False
            and incident_payload["simulation_only"] is True
            and incident_payload["live_execution_enabled"] is False
            and incident_payload["broker_execution_enabled"] is False
        )
        return show("Backup routes are registered and endpoints work", passed)
    except Exception as exc:
        return show("Backup routes are registered and endpoints work", False, str(exc))


def verify_preserved_routes_and_safety() -> bool:
    try:
        from backend.main import app
        from tests.regression_routes_verification import REQUIRED_GET_ROUTES, REQUIRED_WEBSOCKET_ROUTES

        registered_get_routes = {
            route.path for route in app.routes if hasattr(route, "methods") and "GET" in route.methods
        }
        registered_websockets = {
            route.path for route in app.routes if route.__class__.__name__ == "APIWebSocketRoute"
        }
        phase10_required = {
            "/deployment/status",
            "/deployment/readiness",
            "/deployment/runtime/status",
            "/monitoring/status",
            "/monitoring/health",
            "/security/status",
            "/backup/status",
            "/backup/strategy",
            "/backup/recovery",
            "/backup/rollback",
            "/backup/incident-response",
        }
        missing = sorted((REQUIRED_GET_ROUTES | phase10_required) - registered_get_routes)
        missing_ws = sorted(REQUIRED_WEBSOCKET_ROUTES - registered_websockets)
        token = "mt5." + "order_send"
        matches = []
        for path in (PROJECT_ROOT / "backend").rglob("*.py"):
            if path.is_file() and token in path.read_text(encoding="utf-8", errors="ignore"):
                matches.append(path.relative_to(PROJECT_ROOT).as_posix())
        passed = not missing and not missing_ws and matches == ["backend/demo_execution/mt5_demo_executor.py"]
        return show("Phase 10 Day 1-5 routes are preserved and no new order_send exists", passed, ", ".join(missing + missing_ws + matches))
    except Exception as exc:
        return show("Phase 10 Day 1-5 routes are preserved and no new order_send exists", False, str(exc))


def verify_module_registry() -> bool:
    try:
        from backend.system_health.module_registry import get_module_registry

        modules = get_module_registry()
        backup_modules = [module for module in modules if module["name"] == "backup_recovery_readiness"]
        passed = (
            len(backup_modules) == 1
            and backup_modules[0]["route"] == "/backup/status"
            and backup_modules[0]["simulation_only"] is True
            and backup_modules[0]["live_execution_enabled"] is False
        )
        return show("System module registry includes backup recovery readiness", passed)
    except Exception as exc:
        return show("System module registry includes backup recovery readiness", False, str(exc))


def main() -> int:
    print("Phase 10 Day 6 Backup, Recovery & Deployment Runbook Verification")
    print("=" * 70)
    checks = [
        verify_files(),
        verify_service_status_and_score(),
        verify_backup_routes(),
        verify_preserved_routes_and_safety(),
        verify_module_registry(),
    ]
    print("=" * 70)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
