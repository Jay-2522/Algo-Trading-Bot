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
        "backend/deployment/__init__.py",
        "backend/deployment/deployment_models.py",
        "backend/deployment/environment_auditor.py",
        "backend/deployment/vps_readiness_checker.py",
        "backend/deployment/mt5_environment_checker.py",
        "backend/deployment/deployment_readiness_service.py",
        "backend/deployment/deployment_health_store.py",
        "backend/api/deployment_routes.py",
        "docs/phase-10-day-1-progress.md",
        "docs/deployment-readiness-checklist.md",
        "scripts/start_backend.ps1",
        "scripts/start_frontend.ps1",
        "scripts/start_all_dev.ps1",
        "scripts/check_deployment_readiness.ps1",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    return show("Deployment package, docs, and startup scripts exist", not missing, ", ".join(missing))


def verify_models_and_services() -> bool:
    try:
        from backend.deployment.deployment_models import (
            DeploymentReadinessStatus,
            EnvironmentAuditResult,
            MT5EnvironmentCheck,
            VPSEnvironmentCheck,
        )
        from backend.deployment.deployment_readiness_service import DeploymentReadinessService
        from backend.deployment.environment_auditor import EnvironmentAuditor
        from backend.deployment.mt5_environment_checker import MT5EnvironmentChecker
        from backend.deployment.vps_readiness_checker import VPSReadinessChecker

        model_ok = all(
            model.model_fields
            for model in [DeploymentReadinessStatus, EnvironmentAuditResult, MT5EnvironmentCheck, VPSEnvironmentCheck]
        )
        service_ok = all(
            cls is not None
            for cls in [DeploymentReadinessService, EnvironmentAuditor, MT5EnvironmentChecker, VPSReadinessChecker]
        )
        return show("Deployment models, auditor, checkers, and readiness service import", model_ok and service_ok)
    except Exception as exc:
        return show("Deployment models, auditor, checkers, and readiness service import", False, str(exc))


def verify_routes_and_endpoints() -> bool:
    try:
        from backend.main import app

        route_methods = {route.path: set(getattr(route, "methods", set()) or set()) for route in app.routes}
        required = [
            "/deployment/status",
            "/deployment/readiness",
            "/deployment/checklist",
            "/deployment/blockers",
            "/deployment/warnings",
        ]
        routes_ok = all("GET" in route_methods.get(route, set()) for route in required)
        client = TestClient(app)
        status = client.get("/deployment/status")
        readiness = client.get("/deployment/readiness")
        checklist = client.get("/deployment/checklist")
        blockers = client.get("/deployment/blockers")
        warnings = client.get("/deployment/warnings")
        status_payload = status.json()
        readiness_payload = readiness.json()
        endpoint_ok = (
            status.status_code == 200
            and readiness.status_code == 200
            and checklist.status_code == 200
            and blockers.status_code == 200
            and warnings.status_code == 200
            and status_payload["simulation_only"] is True
            and status_payload["demo_execution"] is True
            and status_payload["live_execution_enabled"] is False
            and status_payload["broker_execution_enabled"] is False
            and readiness_payload["simulation_only"] is True
            and readiness_payload["demo_execution"] is True
            and readiness_payload["live_execution_enabled"] is False
            and readiness_payload["broker_execution_enabled"] is False
            and isinstance(status_payload["deployment_score"], int)
            and "Mumbai" in checklist.json()["recommended_region"]
        )
        return show("Deployment routes registered and endpoints work safely", routes_ok and endpoint_ok)
    except Exception as exc:
        return show("Deployment routes registered and endpoints work safely", False, str(exc))


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
        required = {
            "/deployment/status",
            "/strategy-execution-bridge/status",
            "/strategy-execution-bridge/operations/status",
            "/strategy/analyze/eurusd",
            "/strategy/confluence/xauusd",
            "/news/status",
            "/news/unified-risk/status",
        }
        missing = sorted((REQUIRED_GET_ROUTES | required) - registered_get_routes)
        missing_ws = sorted(REQUIRED_WEBSOCKET_ROUTES - registered_websockets)
        token = "mt5." + "order_send"
        matches = []
        for path in (PROJECT_ROOT / "backend").rglob("*.py"):
            if path.is_file() and token in path.read_text(encoding="utf-8", errors="ignore"):
                matches.append(path.relative_to(PROJECT_ROOT).as_posix())
        passed = not missing and not missing_ws and matches == ["backend/demo_execution/mt5_demo_executor.py"]
        return show("Phase 9, strategy, news routes and order_send isolation are preserved", passed, ", ".join(missing + missing_ws + matches))
    except Exception as exc:
        return show("Phase 9, strategy, news routes and order_send isolation are preserved", False, str(exc))


def main() -> int:
    print("Phase 10 Day 1 Deployment Readiness Verification")
    print("=" * 58)
    checks = [
        verify_files(),
        verify_models_and_services(),
        verify_routes_and_endpoints(),
        verify_preserved_routes_and_safety(),
    ]
    print("=" * 58)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
