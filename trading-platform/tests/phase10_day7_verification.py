import subprocess
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
        "backend/deployment/production_readiness_models.py",
        "backend/deployment/production_readiness_service.py",
        "backend/deployment/go_live_assessment.py",
        "backend/api/production_readiness_routes.py",
        "scripts/production_readiness_check.ps1",
        "docs/phase-10-day-7-progress.md",
        "docs/production-readiness-report.md",
        "docs/vps-deployment-checklist-final.md",
        "docs/go-live-assessment.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    return show("Production readiness files, docs, and script exist", not missing, ", ".join(missing))


def verify_service_report_and_assessment() -> bool:
    try:
        from backend.deployment.go_live_assessment import GoLiveAssessmentService
        from backend.deployment.production_readiness_models import GoLiveAssessment, ProductionReadinessReport
        from backend.deployment.production_readiness_service import ProductionReadinessService

        service = ProductionReadinessService(PROJECT_ROOT)
        report = service.get_report()
        assessment = GoLiveAssessmentService(PROJECT_ROOT, service).run_assessment()
        valid_statuses = {"READY_FOR_DEMO_VPS", "READY_FOR_STAGING", "NEEDS_WORK", "BLOCKED"}
        passed = (
            isinstance(report, ProductionReadinessReport)
            and isinstance(assessment, GoLiveAssessment)
            and report.overall_status in valid_statuses
            and 0 <= report.readiness_score <= 100
            and 0 <= report.deployment_score <= 100
            and 0 <= report.monitoring_score <= 100
            and 0 <= report.security_score <= 100
            and 0 <= report.backup_score <= 100
            and 0 <= report.execution_score <= 100
            and 0 <= report.strategy_score <= 100
            and 0 <= report.vps_score <= 100
            and bool(report.recommendations)
            and bool(assessment.next_actions)
            and assessment.readiness_score == report.readiness_score
            and report.simulation_only is True
            and report.demo_execution is True
            and report.live_execution_enabled is False
            and report.broker_execution_enabled is False
        )
        return show("Readiness report, score, status, and assessment work", passed)
    except Exception as exc:
        return show("Readiness report, score, status, and assessment work", False, str(exc))


def verify_routes() -> bool:
    try:
        from backend.main import app

        required = [
            "/production-readiness/status",
            "/production-readiness/report",
            "/production-readiness/assessment",
            "/production-readiness/blockers",
            "/production-readiness/recommendations",
        ]
        route_methods = {route.path: set(getattr(route, "methods", set()) or set()) for route in app.routes}
        routes_ok = all("GET" in route_methods.get(route, set()) for route in required)
        client = TestClient(app)
        responses = {route: client.get(route) for route in required}
        report = responses["/production-readiness/report"].json()
        assessment = responses["/production-readiness/assessment"].json()
        recommendations = responses["/production-readiness/recommendations"].json()
        passed = (
            routes_ok
            and all(response.status_code == 200 for response in responses.values())
            and "readiness_score" in report
            and "overall_status" in report
            and "readiness_score" in assessment
            and bool(recommendations["recommendations"])
            and report["simulation_only"] is True
            and report["demo_execution"] is True
            and report["live_execution_enabled"] is False
            and report["broker_execution_enabled"] is False
        )
        return show("Production readiness routes are registered and working", passed)
    except Exception as exc:
        return show("Production readiness routes are registered and working", False, str(exc))


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
            "/strategy-execution-bridge/demo-approval/status",
            "/strategy-execution-bridge/operations/status",
            "/deployment/status",
            "/deployment/runtime/status",
            "/monitoring/status",
            "/security/status",
            "/backup/status",
            "/production-readiness/status",
        }
        missing = sorted((REQUIRED_GET_ROUTES | required) - registered_get_routes)
        missing_ws = sorted(REQUIRED_WEBSOCKET_ROUTES - registered_websockets)
        token = "mt5." + "order_send"
        matches = []
        for path in (PROJECT_ROOT / "backend").rglob("*.py"):
            if path.is_file() and token in path.read_text(encoding="utf-8", errors="ignore"):
                matches.append(path.relative_to(PROJECT_ROOT).as_posix())
        passed = not missing and not missing_ws and matches == ["backend/demo_execution/mt5_demo_executor.py"]
        return show("Phase 9 and Phase 10 Day 1-6 routes are preserved and no new order_send exists", passed, ", ".join(missing + missing_ws + matches))
    except Exception as exc:
        return show("Phase 9 and Phase 10 Day 1-6 routes are preserved and no new order_send exists", False, str(exc))


def verify_module_registry() -> bool:
    try:
        from backend.system_health.module_registry import get_module_registry

        modules = get_module_registry()
        production = [module for module in modules if module["name"] == "production_readiness_certification"]
        passed = (
            len(production) == 1
            and production[0]["route"] == "/production-readiness/status"
            and production[0]["simulation_only"] is True
            and production[0]["live_execution_enabled"] is False
        )
        return show("System module registry includes production readiness certification", passed)
    except Exception as exc:
        return show("System module registry includes production readiness certification", False, str(exc))


def verify_frontend_build() -> bool:
    try:
        result = subprocess.run(
            ["npm.cmd", "run", "build"],
            cwd=PROJECT_ROOT / "frontend",
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        detail = (result.stderr or result.stdout).splitlines()[-1] if result.returncode else ""
        return show("Frontend build still passes", result.returncode == 0, detail)
    except Exception as exc:
        return show("Frontend build still passes", False, str(exc))


def main() -> int:
    print("Phase 10 Day 7 Production Readiness Certification Verification")
    print("=" * 68)
    checks = [
        verify_files(),
        verify_service_report_and_assessment(),
        verify_routes(),
        verify_preserved_routes_and_safety(),
        verify_module_registry(),
        verify_frontend_build(),
    ]
    print("=" * 68)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
