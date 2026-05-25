import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def print_result(name: str, passed: bool, detail: str = "") -> None:
    status = "PASS" if passed else "FAIL"
    suffix = f" - {detail}" if detail else ""
    print(f"[{status}] {name}{suffix}")


def verify_path(path: str, label: str, is_dir: bool = False) -> bool:
    target = PROJECT_ROOT / path
    passed = target.is_dir() if is_dir else target.is_file()
    print_result(label, passed, "" if passed else path)
    return passed


def verify_routes_and_app() -> bool:
    try:
        from backend.main import app

        paths = {route.path for route in app.routes}
        expected = {
            "/health",
            "/status",
            "/market-data/timeframes",
            "/strategy/session",
            "/risk/status",
            "/execution/status",
            "/mt5/status",
            "/database/status",
            "/ai/status",
            "/news/status",
            "/orchestration/status",
            "/backtesting/status",
            "/streaming/status",
            "/trading-loop/status",
            "/trade-journal/status",
            "/system/status",
            "/system/readiness",
            "/system/safety-scan",
            "/system/routes",
            "/system/phase-report",
            "/system/config-summary",
            "/institutional/status",
        }
        missing = sorted(expected - paths)
        passed = not missing
        print_result("FastAPI app imports with system and existing routes registered", passed, str(missing))
        return passed
    except Exception as exc:
        print_result("FastAPI app imports with system and existing routes registered", False, str(exc))
        return False


def verify_safety_scan() -> bool:
    try:
        from backend.system_health.safety_scanner import SafetyScanner

        result = SafetyScanner().scan()
        passed = (
            result.passed
            and not result.order_send_found
            and not result.live_execution_enabled
            and not result.unsafe_files
        )
        print_result("Safety scanner confirms no broker submission or live-enable source", passed, str(result.unsafe_files))
        return passed
    except Exception as exc:
        print_result("Safety scanner confirms no broker submission or live-enable source", False, str(exc))
        return False


def verify_audit_and_readiness() -> bool:
    try:
        from backend.main import app
        from backend.system_health.module_registry import get_module_registry
        from backend.system_health.readiness_checker import ReadinessChecker
        from backend.system_health.route_auditor import RouteAuditor

        audit = RouteAuditor(app).audit()
        readiness = ReadinessChecker(app).check()
        passed = (
            audit.passed
            and not audit.missing_routes
            and not audit.duplicate_paths
            and readiness.overall_status == "READY"
            and readiness.safety_passed
            and len(readiness.modules) == len(get_module_registry())
            and len(readiness.modules) >= 15
            and all(not module.live_execution_enabled for module in readiness.modules)
        )
        print_result("Route auditor and readiness checker certify all Phase 1 modules", passed)
        return passed
    except Exception as exc:
        print_result("Route auditor and readiness checker certify all Phase 1 modules", False, str(exc))
        return False


def verify_phase_report() -> bool:
    try:
        from backend.main import app
        from backend.system_health.system_health_service import SystemHealthService

        report = SystemHealthService(app).get_phase_report()
        passed = (
            report.phase == "PHASE_1_BACKEND_FOUNDATION"
            and len(report.completed_days) == 15
            and len(report.completed_modules) == 15
            and "System Health + Hardening" in report.completed_modules
            and report.safety_status == "PASSED"
        )
        print_result("Phase report includes Days 1-15 and successful safety status", passed)
        return passed
    except Exception as exc:
        print_result("Phase report includes Days 1-15 and successful safety status", False, str(exc))
        return False


def verify_status_and_lifecycle_api() -> bool:
    try:
        from backend.api.trading_loop_routes import trading_loop_service
        from backend.main import app

        with TestClient(app) as client:
            status = client.get("/system/status")
            readiness = client.get("/system/readiness")
            safety = client.get("/system/safety-scan")
            routes = client.get("/system/routes")
            report = client.get("/system/phase-report")
            config = client.get("/system/config-summary")
            started = client.post("/trading-loop/start")
        stopped_on_shutdown = not trading_loop_service.get_status().running
        passed = (
            status.status_code == 200
            and status.json()["status"] == "operational"
            and status.json()["phase"] == "PHASE_1_BACKEND_FOUNDATION"
            and status.json()["live_execution_enabled"] is False
            and status.json()["simulation_only"] is True
            and status.json()["modules_online"] >= 15
            and readiness.json()["overall_status"] == "READY"
            and safety.json()["passed"] is True
            and routes.json()["passed"] is True
            and report.json()["readiness_status"] == "READY"
            and config.json()["live_execution_enabled"] is False
            and started.status_code == 200
            and stopped_on_shutdown
        )
        print_result("System APIs are JSON-safe and application shutdown cleans up scheduler", passed)
        return passed
    except Exception as exc:
        print_result("System APIs are JSON-safe and application shutdown cleans up scheduler", False, str(exc))
        return False


def verify_single_app_instance() -> bool:
    main_source = (PROJECT_ROOT / "backend/main.py").read_text(encoding="utf-8")
    passed = main_source.count("app = FastAPI(") == 1
    print_result("Backend main declares one FastAPI application instance", passed)
    return passed


def main() -> int:
    print("Day 15 Full Integration and Stability Hardening Verification")
    print("=" * 60)
    checks = [
        verify_path("backend/system_health", "system_health package exists", is_dir=True),
        verify_path("backend/system_health/health_models.py", "health_models.py exists"),
        verify_path("backend/system_health/module_registry.py", "module_registry.py exists"),
        verify_path("backend/system_health/safety_scanner.py", "safety_scanner.py exists"),
        verify_path("backend/system_health/route_auditor.py", "route_auditor.py exists"),
        verify_path("backend/system_health/readiness_checker.py", "readiness_checker.py exists"),
        verify_path("backend/system_health/system_health_service.py", "system_health_service.py exists"),
        verify_path("backend/system_health/phase_report.py", "phase_report.py exists"),
        verify_path("backend/api/system_health_routes.py", "system_health_routes.py exists"),
        verify_routes_and_app(),
        verify_safety_scan(),
        verify_audit_and_readiness(),
        verify_phase_report(),
        verify_status_and_lifecycle_api(),
        verify_single_app_instance(),
    ]
    print("=" * 60)
    passed = all(checks)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
