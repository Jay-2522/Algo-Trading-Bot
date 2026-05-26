import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def app_route_paths() -> list[str]:
    from backend.main import app

    return [route.path for route in app.routes]


def verify_files_and_routes() -> bool:
    files = [
        "backend/institutional_intelligence/phase2_completion_models.py",
        "backend/institutional_intelligence/phase2_readiness_checker.py",
        "backend/institutional_intelligence/phase2_module_registry.py",
        "backend/institutional_intelligence/phase2_safety_auditor.py",
        "backend/institutional_intelligence/phase2_completion_report_builder.py",
        "docs/phase-2-day-19-progress.md",
    ]
    files_ok = all((PROJECT_ROOT / path).is_file() for path in files)
    expected = {
        "/institutional/dashboard/{symbol}",
        "/institutional/phase2/status",
        "/institutional/phase2/readiness",
        "/institutional/phase2/safety-audit",
        "/institutional/phase2/completion-report",
        "/institutional/phase2/modules",
    }
    routes_ok = expected <= set(app_route_paths())
    return show("Day 19 files and final Phase 2 routes are registered", files_ok and routes_ok)


def verify_registry_and_readiness() -> bool:
    try:
        from backend.institutional_intelligence.phase2_completion_report_builder import Phase2CompletionReportBuilder
        from backend.institutional_intelligence.phase2_module_registry import Phase2ModuleRegistry

        registry = Phase2ModuleRegistry()
        report = Phase2CompletionReportBuilder().build_report(app_route_paths())
        modules = {module.module_name for module in report.module_statuses}
        passed = (
            len(registry.MODULE_ROUTES) == 19
            and len(modules) == 19
            and "dashboard_context" in modules
            and "phase2_completion" in modules
            and report.overall_status == "READY"
            and len(report.completed_modules) == 19
            and report.missing_routes == []
            and report.dashboard_ready
            and report.reasoning_ready
            and report.orchestration_ready
            and report.performance_ready
            and report.summary == "Phase 2 Institutional Intelligence Layer is complete in simulation-only mode."
        )
        return show("Registry and readiness checker certify all nineteen institutional modules", passed)
    except Exception as exc:
        return show("Registry and readiness checker certify all nineteen institutional modules", False, str(exc))


def verify_safety_auditor() -> bool:
    try:
        from backend.institutional_intelligence.phase2_safety_auditor import Phase2SafetyAuditor

        safe = Phase2SafetyAuditor().run_safety_audit()
        with TemporaryDirectory() as directory:
            backend = Path(directory)
            unsafe = "def submit(mt5):\n    return mt5." + "order_send({'unsafe': True})\n"
            (backend / "unsafe.py").write_text(unsafe, encoding="utf-8")
            detected = Phase2SafetyAuditor(backend).run_safety_audit()
        passed = (
            safe.passed is True
            and safe.simulation_only is True
            and safe.live_execution_enabled is False
            and safe.order_send_found is False
            and detected.passed is False
            and detected.order_send_found is True
            and len(detected.unsafe_patterns) >= 1
        )
        return show("Safety auditor passes safe source and detects prohibited submission code", passed)
    except Exception as exc:
        return show("Safety auditor passes safe source and detects prohibited submission code", False, str(exc))


def verify_api_and_health_integration() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        endpoints = [
            "/institutional/phase2/status",
            "/institutional/phase2/readiness",
            "/institutional/phase2/safety-audit",
            "/institutional/phase2/completion-report",
            "/institutional/phase2/modules",
        ]
        responses = [client.get(endpoint) for endpoint in endpoints]
        status = responses[0].json()
        safety = responses[2].json()
        modules = responses[4].json()
        readiness = client.get("/system/readiness").json()
        route_audit = client.get("/system/routes").json()
        passed = (
            all(response.status_code == 200 for response in responses)
            and status["overall_status"] == "READY"
            and status["simulation_only"] is True
            and status["live_execution_enabled"] is False
            and safety["passed"] is True
            and safety["order_send_found"] is False
            and len(modules) == 19
            and all(module["live_execution_enabled"] is False for module in modules)
            and any(
                module["module_name"] == "institutional_phase2_completion"
                for module in readiness["modules"]
            )
            and route_audit["passed"] is True
            and route_audit["missing_routes"] == []
        )
        return show("Final APIs are JSON-safe and registered in system health readiness", passed)
    except Exception as exc:
        return show("Final APIs are JSON-safe and registered in system health readiness", False, str(exc))


def main() -> int:
    print("Phase 2 Day 19 Final Institutional Integration Verification")
    print("=" * 62)
    tests = [
        verify_files_and_routes(),
        verify_registry_and_readiness(),
        verify_safety_auditor(),
        verify_api_and_health_integration(),
    ]
    print("=" * 62)
    print("PASS" if all(tests) else "FAIL")
    return 0 if all(tests) else 1


if __name__ == "__main__":
    raise SystemExit(main())
