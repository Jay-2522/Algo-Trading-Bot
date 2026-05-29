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
        "backend/execution_dashboard/__init__.py",
        "backend/execution_dashboard/execution_dashboard_models.py",
        "backend/execution_dashboard/execution_dashboard_builder.py",
        "backend/execution_dashboard/execution_dashboard_service.py",
        "backend/api/execution_dashboard_routes.py",
        "frontend/components/dashboard/ExecutionOverviewPanel.tsx",
        "frontend/components/dashboard/ExecutionHealthCards.tsx",
        "frontend/components/dashboard/ExecutionSummaryPanel.tsx",
        "frontend/components/dashboard/ExecutionReadinessPanel.tsx",
        "frontend/lib/execution-dashboard-api.ts",
        "docs/phase-5-day-7-progress.md",
    ]
    return show("Execution dashboard backend, frontend, and docs files exist", all((PROJECT_ROOT / path).is_file() for path in files))


def verify_routes_registered() -> bool:
    try:
        from backend.main import app

        routes = {route.path for route in app.routes}
        expected = {
            "/execution-dashboard/status",
            "/execution-dashboard/overview",
            "/execution-dashboard/cards",
            "/execution-dashboard/summary",
        }
        return show("Execution dashboard routes registered", expected <= routes)
    except Exception as exc:
        return show("Execution dashboard routes registered", False, str(exc))


def verify_service_works() -> bool:
    try:
        from backend.api.execution_dashboard_routes import execution_dashboard_service

        status = execution_dashboard_service.status()
        overview = execution_dashboard_service.overview()
        cards = execution_dashboard_service.cards()
        summary = execution_dashboard_service.summary()
        passed = (
            status["status"] == "OPERATIONAL"
            and status["simulation_only"] is True
            and status["live_execution_enabled"] is False
            and status["broker_execution_enabled"] is False
            and overview.simulation_only is True
            and overview.live_execution_enabled is False
            and overview.broker_execution_enabled is False
            and len(cards) >= 8
            and summary.total_reconciliations >= 1
        )
        return show("Execution dashboard service builds status, overview, cards, and summary", passed)
    except Exception as exc:
        return show("Execution dashboard service builds status, overview, cards, and summary", False, str(exc))


def verify_endpoints() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        status = client.get("/execution-dashboard/status")
        overview = client.get("/execution-dashboard/overview")
        cards = client.get("/execution-dashboard/cards")
        summary = client.get("/execution-dashboard/summary")
        overview_payload = overview.json()
        passed = (
            status.status_code == 200
            and overview.status_code == 200
            and cards.status_code == 200
            and summary.status_code == 200
            and overview_payload.get("simulation_only") is True
            and overview_payload.get("live_execution_enabled") is False
            and overview_payload.get("broker_execution_enabled") is False
            and isinstance(cards.json(), list)
            and "blocked_attempts" in summary.json()
        )
        return show("Execution dashboard endpoints return read-only dashboard payloads", passed)
    except Exception as exc:
        return show("Execution dashboard endpoints return read-only dashboard payloads", False, str(exc))


def verify_frontend_integration() -> bool:
    developer_shell = (PROJECT_ROOT / "frontend/components/dashboard/DeveloperDashboardShell.tsx").read_text(encoding="utf-8")
    developer_page = (PROJECT_ROOT / "frontend/app/dashboard/developer/page.tsx").read_text(encoding="utf-8")
    api = (PROJECT_ROOT / "frontend/lib/dashboard-api.ts").read_text(encoding="utf-8")
    passed = (
        "ExecutionOverviewPanel" in developer_shell
        and "ExecutionHealthCards" in developer_shell
        and "ExecutionSummaryPanel" in developer_shell
        and "ExecutionReadinessPanel" in developer_shell
        and "DeveloperDashboardShell" in developer_page
        and "force-dynamic" in developer_page
        and "/execution-dashboard/status" in api
        and "/execution-dashboard/overview" in api
        and "/execution-dashboard/cards" in api
        and "/execution-dashboard/summary" in api
    )
    return show("Developer dashboard page and API bundle include execution operations panels", passed)


def verify_module_registry() -> bool:
    try:
        from backend.system_health.module_registry import get_module_registry

        modules = get_module_registry()
        passed = any(module["name"] == "execution_operations_dashboard" and module["route"] == "/execution-dashboard/status" for module in modules)
        return show("Execution dashboard appears in module registry", passed)
    except Exception as exc:
        return show("Execution dashboard appears in module registry", False, str(exc))


def verify_order_send_isolated() -> bool:
    token = "mt5." + "order_send"
    matches = []
    for path in (PROJECT_ROOT / "backend").rglob("*.py"):
        if path.is_file() and token in path.read_text(encoding="utf-8", errors="ignore"):
            matches.append(path.relative_to(PROJECT_ROOT).as_posix())
    passed = matches == ["backend/demo_execution/mt5_demo_executor.py"]
    return show("MT5 order submission remains isolated to guarded demo executor", passed, ", ".join(matches))


def verify_previous_routes_preserved() -> bool:
    try:
        from backend.main import app
        from tests.regression_routes_verification import REQUIRED_GET_ROUTES, REQUIRED_WEBSOCKET_ROUTES

        registered_get_routes = {
            route.path
            for route in app.routes
            if hasattr(route, "methods") and "GET" in route.methods
        }
        registered_websockets = {
            route.path
            for route in app.routes
            if route.__class__.__name__ == "APIWebSocketRoute"
        }
        missing = sorted(REQUIRED_GET_ROUTES - registered_get_routes)
        missing_ws = sorted(REQUIRED_WEBSOCKET_ROUTES - registered_websockets)
        return show("All regression routes remain registered", not missing and not missing_ws, ", ".join(missing + missing_ws))
    except Exception as exc:
        return show("All regression routes remain registered", False, str(exc))


def main() -> int:
    print("Phase 5 Day 7 Execution Dashboard Verification")
    print("=" * 56)
    checks = [
        verify_files(),
        verify_routes_registered(),
        verify_service_works(),
        verify_endpoints(),
        verify_frontend_integration(),
        verify_module_registry(),
        verify_order_send_isolated(),
        verify_previous_routes_preserved(),
    ]
    print("=" * 56)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
