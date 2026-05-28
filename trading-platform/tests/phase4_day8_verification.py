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
        "backend/portfolio/__init__.py",
        "backend/portfolio/portfolio_models.py",
        "backend/portfolio/portfolio_summary_builder.py",
        "backend/portfolio/account_analytics_service.py",
        "backend/portfolio/exposure_summary_service.py",
        "backend/portfolio/portfolio_service.py",
        "backend/api/portfolio_routes.py",
        "docs/phase-4-day-8-progress.md",
    ]
    return show("Portfolio backend package and documentation exist", all((PROJECT_ROOT / path).is_file() for path in files))


def verify_portfolio_routes_and_payloads() -> bool:
    try:
        from backend.main import app

        routes = {route.path for route in app.routes}
        expected = {
            "/portfolio/status",
            "/portfolio/overview",
            "/portfolio/accounts",
            "/portfolio/exposure",
            "/portfolio/pnl-summary",
        }
        client = TestClient(app)
        status = client.get("/portfolio/status")
        overview = client.get("/portfolio/overview")
        accounts = client.get("/portfolio/accounts")
        exposure = client.get("/portfolio/exposure")
        pnl = client.get("/portfolio/pnl-summary")
        account_ids = {account.get("account_id") for account in accounts.json()}
        exposure_json = exposure.json()
        overview_json = overview.json()
        nifty = exposure_json.get("exposure_by_symbol", {}).get("NIFTY50", {})
        passed = (
            expected <= routes
            and status.status_code == 200
            and overview.status_code == 200
            and accounts.status_code == 200
            and exposure.status_code == 200
            and pnl.status_code == 200
            and {"STARTRADER_DEMO_1", "FXPRO_DEMO_1", "VANTAGE_DEMO_1"} <= account_ids
            and "NIFTY50" in exposure_json.get("blocked_symbols", [])
            and "BLOCK" in str(nifty.get("status", ""))
            and overview_json.get("simulation_only") is True
            and overview_json.get("live_execution_enabled") is False
            and pnl.json().get("simulation_only") is True
        )
        return show("Portfolio routes return JSON-safe simulated analytics", passed)
    except Exception as exc:
        return show("Portfolio routes return JSON-safe simulated analytics", False, str(exc))


def verify_frontend_files() -> bool:
    files = [
        "frontend/components/dashboard/PortfolioOverviewPanel.tsx",
        "frontend/components/dashboard/AccountAnalyticsPanel.tsx",
        "frontend/components/dashboard/ExposureSummaryPanel.tsx",
        "frontend/components/dashboard/SimulatedPnlPanel.tsx",
    ]
    return show("Portfolio dashboard components exist", all((PROJECT_ROOT / path).is_file() for path in files))


def verify_frontend_integration() -> bool:
    try:
        api = (PROJECT_ROOT / "frontend/lib/dashboard-api.ts").read_text(encoding="utf-8")
        shell = (PROJECT_ROOT / "frontend/components/dashboard/DashboardShell.tsx").read_text(encoding="utf-8")
        passed = (
            "/portfolio/status" in api
            and "/portfolio/overview" in api
            and "/portfolio/accounts" in api
            and "/portfolio/exposure" in api
            and "/portfolio/pnl-summary" in api
            and "PortfolioOverviewPanel" in shell
            and "AccountAnalyticsPanel" in shell
            and "ExposureSummaryPanel" in shell
            and "SimulatedPnlPanel" in shell
        )
        return show("Dashboard API helper and shell include portfolio analytics", passed)
    except Exception as exc:
        return show("Dashboard API helper and shell include portfolio analytics", False, str(exc))


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
    print("Phase 4 Day 8 Portfolio Analytics Verification")
    print("=" * 52)
    checks = [
        verify_backend_files(),
        verify_portfolio_routes_and_payloads(),
        verify_frontend_files(),
        verify_frontend_integration(),
        verify_safety(),
    ]
    print("=" * 52)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
