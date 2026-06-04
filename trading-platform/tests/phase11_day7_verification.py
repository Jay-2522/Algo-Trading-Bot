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
        "backend/client_analytics/executive_models.py",
        "backend/client_analytics/readiness_aggregator.py",
        "backend/client_analytics/executive_dashboard_service.py",
        "frontend/components/executive-dashboard/ExecutiveDashboardSection.tsx",
        "frontend/components/executive-dashboard/SystemReadinessCards.tsx",
        "frontend/components/executive-dashboard/InstrumentReadinessPanel.tsx",
        "frontend/components/executive-dashboard/SystemHealthPanel.tsx",
        "frontend/components/executive-dashboard/ProductionReadinessPanel.tsx",
        "frontend/components/executive-dashboard/ExecutiveSummaryPanel.tsx",
        "frontend/lib/executiveDashboardApi.ts",
        "docs/phase-11-day-7-progress.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    return show("Executive backend, frontend, API client, and docs exist", not missing, ", ".join(missing))


def verify_executive_routes() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        route_paths = {route.path for route in app.routes if hasattr(route, "methods") and "GET" in route.methods}
        required = {
            "/client-analytics/executive/status",
            "/client-analytics/executive/summary",
            "/client-analytics/executive/readiness",
            "/client-analytics/executive/instruments",
            "/client-analytics/executive/system-health",
            "/client-analytics/executive/completion",
        }
        summary = client.get("/client-analytics/executive/summary")
        readiness = client.get("/client-analytics/executive/readiness")
        instruments = client.get("/client-analytics/executive/instruments")
        completion = client.get("/client-analytics/executive/completion")
        summary_payload = summary.json()
        instrument_payload = instruments.json()
        completion_payload = completion.json()
        nifty = next((item for item in instrument_payload["instruments"] if item["symbol"] == "NIFTY50"), {})
        passed = (
            required <= route_paths
            and summary.status_code == 200
            and readiness.status_code == 200
            and instruments.status_code == 200
            and completion.status_code == 200
            and summary_payload["simulation_only"] is True
            and summary_payload["demo_execution"] is True
            and summary_payload["live_execution_enabled"] is False
            and summary_payload["broker_execution_enabled"] is False
            and summary_payload["overall_completion_percentage"] < 100
            and summary_payload["nifty50_ready"] is False
            and nifty["status"] in {
                "PENDING_IMPLEMENTATION",
                "FOUNDATION_READY",
                "STRATEGY_FOUNDATION_READY",
                "MARKET_DATA_READY",
                "SMC_INTELLIGENCE_READY",
                "RISK_QUALIFICATION_READY",
                "EXECUTION_BRIDGE_READY",
            }
            and nifty["ready"] is False
            and completion_payload["overall_completion_percentage"] < 100
        )
        return show("Executive routes, summary, readiness, instruments, completion, and safety flags work", passed)
    except Exception as exc:
        return show("Executive routes, summary, readiness, instruments, completion, and safety flags work", False, str(exc))


def verify_dashboard_ui() -> bool:
    try:
        page = (PROJECT_ROOT / "frontend" / "app" / "dashboard" / "page.tsx").read_text(encoding="utf-8")
        shell = (PROJECT_ROOT / "frontend" / "components" / "dashboard" / "DashboardShell.tsx").read_text(encoding="utf-8")
        section = (PROJECT_ROOT / "frontend" / "components" / "executive-dashboard" / "ExecutiveDashboardSection.tsx").read_text(encoding="utf-8")
        readiness = (PROJECT_ROOT / "frontend" / "components" / "executive-dashboard" / "SystemReadinessCards.tsx").read_text(encoding="utf-8")
        instruments = (PROJECT_ROOT / "frontend" / "components" / "executive-dashboard" / "InstrumentReadinessPanel.tsx").read_text(encoding="utf-8")
        health = (PROJECT_ROOT / "frontend" / "components" / "executive-dashboard" / "SystemHealthPanel.tsx").read_text(encoding="utf-8")
        production = (PROJECT_ROOT / "frontend" / "components" / "executive-dashboard" / "ProductionReadinessPanel.tsx").read_text(encoding="utf-8")
        summary = (PROJECT_ROOT / "frontend" / "components" / "executive-dashboard" / "ExecutiveSummaryPanel.tsx").read_text(encoding="utf-8")
        api = (PROJECT_ROOT / "frontend" / "lib" / "executiveDashboardApi.ts").read_text(encoding="utf-8")
        passed = (
            "ExecutiveDashboardSection" in page
            and "executiveDashboardSection" in shell
            and "Executive Command Center" in section
            and "A complete operational view of analytics, execution, reporting, account synchronization, deployment readiness, and instrument coverage." in section
            and "Analytics" in api
            and "Reports" in api
            and "Accounts" in api
            and "Copier" in api
            and "Strategy" in api
            and "Deployment" in api
            and "Monitoring" in api
            and "Security" in api
            and "Production" in api
            and (
                "PENDING IMPLEMENTATION" in api
                or "FOUNDATION READY / BROKER PENDING" in api
                or "STRATEGY FOUNDATION READY / BROKER PENDING" in api
                or "MARKET DATA READY / STRATEGY PENDING" in api
                or "SMC INTELLIGENCE READY / EXECUTION PENDING" in api
                or "RISK QUALIFICATION READY / EXECUTION PENDING" in api
                or "EXECUTION BRIDGE READY / ORDER PLACEMENT DISABLED" in api
            )
            and "Instrument Readiness" in instruments
            and "System Health" in health
            and "Production Readiness" in production
            and "Executive Summary" in summary
            and "SystemReadinessCards" in section
            and "READY" in readiness
        )
        return show("Executive dashboard UI, readiness cards, panels, imports, and NIFTY50 pending label exist", passed)
    except Exception as exc:
        return show("Executive dashboard UI, readiness cards, panels, imports, and NIFTY50 pending label exist", False, str(exc))


def verify_no_order_send() -> bool:
    try:
        token = "mt5." + "order_send"
        matches = []
        for path in (PROJECT_ROOT / "backend").rglob("*.py"):
            if path.is_file() and token in path.read_text(encoding="utf-8", errors="ignore"):
                matches.append(path.relative_to(PROJECT_ROOT).as_posix())
        return show("No new mt5.order_send added", matches == ["backend/demo_execution/mt5_demo_executor.py"], ", ".join(matches))
    except Exception as exc:
        return show("No new mt5.order_send added", False, str(exc))


def verify_phase11_preserved() -> bool:
    try:
        from backend.main import app

        required = {
            "/client-analytics/status",
            "/client-analytics/overview",
            "/client-analytics/accounts",
            "/client-analytics/reports/status",
            "/client-analytics/strategy/status",
            "/client-analytics/strategy/overview",
            "/client-analytics/strategy/comparison",
            "/client-analytics/executive/status",
        }
        registered = {route.path for route in app.routes if hasattr(route, "methods") and "GET" in route.methods}
        return show("Phase 11 Day 1-6 routes are preserved", required <= registered)
    except Exception as exc:
        return show("Phase 11 Day 1-6 routes are preserved", False, str(exc))


def verify_frontend_build() -> bool:
    try:
        result = subprocess.run(
            ["npm.cmd", "run", "build"],
            cwd=PROJECT_ROOT / "frontend",
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        detail = (result.stderr or result.stdout).splitlines()[-1] if result.returncode else ""
        return show("Frontend build expected to pass", result.returncode == 0, detail)
    except Exception as exc:
        return show("Frontend build expected to pass", False, str(exc))


def main() -> int:
    print("Phase 11 Day 7 Executive Command Center Verification")
    print("=" * 64)
    checks = [
        verify_files(),
        verify_executive_routes(),
        verify_dashboard_ui(),
        verify_no_order_send(),
        verify_phase11_preserved(),
        verify_frontend_build(),
    ]
    print("=" * 64)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
