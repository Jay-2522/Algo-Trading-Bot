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
        "backend/demo_mode/__init__.py",
        "backend/demo_mode/demo_mode_models.py",
        "backend/demo_mode/executive_overview_builder.py",
        "backend/demo_mode/client_demo_service.py",
        "backend/api/demo_mode_routes.py",
        "docs/phase-4-day-7-progress.md",
    ]
    return show("Demo mode backend package and documentation exist", all((PROJECT_ROOT / path).is_file() for path in files))


def verify_routes_and_payloads() -> bool:
    try:
        from backend.main import app

        routes = {route.path for route in app.routes}
        expected = {
            "/demo-mode/status",
            "/demo-mode/overview",
            "/demo-mode/kpis",
            "/demo-mode/pipeline-summary",
        }
        client = TestClient(app)
        status = client.get("/demo-mode/status")
        overview = client.get("/demo-mode/overview")
        kpis = client.get("/demo-mode/kpis")
        pipeline = client.get("/demo-mode/pipeline-summary")
        overview_json = overview.json()
        markets = " ".join(overview_json.get("supported_markets", []))
        brokers = " ".join(overview_json.get("supported_brokers", []))
        safety = " ".join(overview_json.get("safety_summary", []))
        passed = (
            expected <= routes
            and status.status_code == 200
            and overview.status_code == 200
            and kpis.status_code == 200
            and pipeline.status_code == 200
            and "EUR/USD" in markets
            and "XAU/USD" in markets
            and "NIFTY 50" in markets
            and "STARTRADER" in brokers
            and "FxPro" in brokers
            and "Vantage" in brokers
            and "disabled" in safety.lower()
            and overview_json.get("simulation_only") is True
            and overview_json.get("live_execution_enabled") is False
            and len(kpis.json()) >= 6
        )
        return show("Demo mode routes are registered and payloads are client-ready", passed)
    except Exception as exc:
        return show("Demo mode routes are registered and payloads are client-ready", False, str(exc))


def verify_frontend_files() -> bool:
    files = [
        "frontend/components/dashboard/ClientDemoModePanel.tsx",
        "frontend/components/dashboard/ExecutiveOverviewPanel.tsx",
        "frontend/components/dashboard/ClientKpiGrid.tsx",
        "frontend/components/dashboard/PipelineReadinessPanel.tsx",
    ]
    return show("Client demo mode frontend components exist", all((PROJECT_ROOT / path).is_file() for path in files))


def verify_frontend_integration() -> bool:
    try:
        api = (PROJECT_ROOT / "frontend/lib/dashboard-api.ts").read_text(encoding="utf-8")
        shell = (PROJECT_ROOT / "frontend/components/dashboard/DashboardShell.tsx").read_text(encoding="utf-8")
        page = (PROJECT_ROOT / "frontend/app/dashboard/page.tsx").read_text(encoding="utf-8")
        passed = (
            "/demo-mode/status" in api
            and "/demo-mode/overview" in api
            and "/demo-mode/kpis" in api
            and "/demo-mode/pipeline-summary" in api
            and "ClientDemoModePanel" in shell
            and "DashboardShell" in page
        )
        return show("Dashboard API helper and page include demo mode", passed)
    except Exception as exc:
        return show("Dashboard API helper and page include demo mode", False, str(exc))


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
    print("Phase 4 Day 7 Client Demo Mode Verification")
    print("=" * 50)
    checks = [
        verify_backend_files(),
        verify_routes_and_payloads(),
        verify_frontend_files(),
        verify_frontend_integration(),
        verify_safety(),
    ]
    print("=" * 50)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
