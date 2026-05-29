import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def verify_backend_files() -> bool:
    files = [
        "backend/operational_intelligence/__init__.py",
        "backend/operational_intelligence/operational_models.py",
        "backend/operational_intelligence/health_aggregator.py",
        "backend/operational_intelligence/warning_engine.py",
        "backend/operational_intelligence/operational_intelligence_service.py",
        "backend/operational_intelligence/monitoring_summary_builder.py",
        "backend/api/operational_intelligence_routes.py",
        "docs/phase-4-day-9-progress.md",
    ]
    return show("Operational intelligence package and documentation exist", all((PROJECT_ROOT / path).is_file() for path in files))


def verify_operational_routes_and_payloads() -> bool:
    try:
        from backend.main import app

        routes = {route.path for route in app.routes}
        expected = {
            "/operational-intelligence/status",
            "/operational-intelligence/health-summary",
            "/operational-intelligence/modules",
            "/operational-intelligence/warnings",
            "/operational-intelligence/health-score",
        }
        client = TestClient(app)
        status = client.get("/operational-intelligence/status")
        summary = client.get("/operational-intelligence/health-summary")
        modules = client.get("/operational-intelligence/modules")
        warnings = client.get("/operational-intelligence/warnings")
        score = client.get("/operational-intelligence/health-score")
        summary_json = summary.json()
        module_names = {module.get("module_name") for module in modules.json()}
        passed = (
            expected <= routes
            and status.status_code == 200
            and summary.status_code == 200
            and modules.status_code == 200
            and warnings.status_code == 200
            and score.status_code == 200
            and isinstance(summary_json.get("health_score"), int)
            and 0 <= summary_json.get("health_score", -1) <= 100
            and summary_json.get("simulation_only") is True
            and summary_json.get("live_execution_enabled") is False
            and {"Brokers", "Webhooks", "Dashboard", "Monitoring", "Control Center", "Portfolio", "Queue Engine", "Orchestration"} <= module_names
            and isinstance(warnings.json(), list)
        )
        return show("Operational routes return JSON-safe health, modules, warnings, and score", passed)
    except Exception as exc:
        return show("Operational routes return JSON-safe health, modules, warnings, and score", False, str(exc))


def verify_frontend_files() -> bool:
    files = [
        "frontend/components/dashboard/OperationalHealthPanel.tsx",
        "frontend/components/dashboard/SystemHealthScore.tsx",
        "frontend/components/dashboard/ModuleStatusGrid.tsx",
        "frontend/components/dashboard/WarningCenter.tsx",
        "frontend/components/dashboard/OperationalInsightsPanel.tsx",
    ]
    return show("Operational intelligence dashboard components exist", all((PROJECT_ROOT / path).is_file() for path in files))


def verify_frontend_integration() -> bool:
    try:
        api = (PROJECT_ROOT / "frontend/lib/dashboard-api.ts").read_text(encoding="utf-8")
        shell = (PROJECT_ROOT / "frontend/components/dashboard/DashboardShell.tsx").read_text(encoding="utf-8")
        passed = (
            "/operational-intelligence/status" in api
            and "/operational-intelligence/health-summary" in api
            and "/operational-intelligence/modules" in api
            and "/operational-intelligence/warnings" in api
            and "/operational-intelligence/health-score" in api
            and "OperationalHealthPanel" in shell
        )
        return show("Dashboard API helper and shell include operational intelligence", passed)
    except Exception as exc:
        return show("Dashboard API helper and shell include operational intelligence", False, str(exc))


def verify_safety() -> bool:
    try:
        source_suffixes = {".py", ".ts", ".tsx", ".js", ".jsx"}
        text = "\n".join(
            path.read_text(encoding="utf-8", errors="ignore")
            for root in ("backend", "frontend")
            for path in (PROJECT_ROOT / root).rglob("*")
            if path.is_file()
            and path.suffix in source_suffixes
            and "node_modules" not in path.parts
            and ".next" not in path.parts
        )
        passed = (
            "mt5.order_send" not in text
            and "order_send(" not in text
            and "live_execution_enabled=True" not in text
            and "broker_execution_enabled=True" not in text
            and "real_trading_enabled=True" not in text
        )
        return show("No live execution patterns were added", passed)
    except Exception as exc:
        return show("No live execution patterns were added", False, str(exc))


def main() -> int:
    print("Phase 4 Day 9 Operational Intelligence Verification")
    print("=" * 56)
    checks = [
        verify_backend_files(),
        verify_operational_routes_and_payloads(),
        verify_frontend_files(),
        verify_frontend_integration(),
        verify_safety(),
    ]
    print("=" * 56)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
