import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def verify_files() -> bool:
    files = [
        "frontend/app/dashboard/page.tsx",
        "frontend/components/dashboard/DashboardShell.tsx",
        "frontend/components/dashboard/DashboardHeader.tsx",
        "frontend/components/dashboard/DashboardCard.tsx",
        "frontend/components/dashboard/DashboardStatusGrid.tsx",
        "frontend/components/dashboard/DashboardAlertsPanel.tsx",
        "frontend/components/dashboard/DashboardSafetyBanner.tsx",
        "frontend/components/dashboard/BrokerStatusPanel.tsx",
        "frontend/components/dashboard/AccountStatusPanel.tsx",
        "frontend/components/dashboard/ExecutionSafetyPanel.tsx",
        "frontend/components/dashboard/StatusBadge.tsx",
        "frontend/lib/dashboard-api.ts",
        "docs/phase-4-day-3-progress.md",
    ]
    return show("Premium dashboard files and components exist", all((PROJECT_ROOT / path).is_file() for path in files))


def verify_api_helper() -> bool:
    try:
        api = (PROJECT_ROOT / "frontend/lib/dashboard-api.ts").read_text(encoding="utf-8")
        expected = [
            "/dashboard/status",
            "/dashboard/overview",
            "/dashboard/cards",
            "/dashboard/summary",
            "/monitoring/alerts",
            "/brokers/status",
            "/accounts/status",
            "/execution-queue/status",
            "/phase3/status",
        ]
        return show("Dashboard API helper includes premium widget endpoints", all(endpoint in api for endpoint in expected))
    except Exception as exc:
        return show("Dashboard API helper includes premium widget endpoints", False, str(exc))


def verify_ui_content() -> bool:
    try:
        shell = (PROJECT_ROOT / "frontend/components/dashboard/DashboardShell.tsx").read_text(encoding="utf-8")
        header = (PROJECT_ROOT / "frontend/components/dashboard/DashboardHeader.tsx").read_text(encoding="utf-8")
        broker = (PROJECT_ROOT / "frontend/components/dashboard/BrokerStatusPanel.tsx").read_text(encoding="utf-8")
        account = (PROJECT_ROOT / "frontend/components/dashboard/AccountStatusPanel.tsx").read_text(encoding="utf-8")
        execution = (PROJECT_ROOT / "frontend/components/dashboard/ExecutionSafetyPanel.tsx").read_text(encoding="utf-8")
        alerts = (PROJECT_ROOT / "frontend/components/dashboard/DashboardAlertsPanel.tsx").read_text(encoding="utf-8")
        passed = (
            "AI Multi-Market Trading Bot" in header
            and "Client VPS Dashboard" in header
            and "BrokerStatusPanel" in shell
            and "AccountStatusPanel" in shell
            and "ExecutionSafetyPanel" in shell
            and "STARTRADER" in broker
            and "FxPro" in broker
            and "Vantage" in broker
            and "STARTRADER_DEMO_1" in account
            and "FXPRO_DEMO_1" in account
            and "VANTAGE_DEMO_1" in account
            and "Queue preparation only" in execution
            and "Simulated lifecycle only" in execution
            and "No live orders enabled" in execution
            and "No active alerts" in alerts
        )
        return show("Premium dashboard UI content is present", passed)
    except Exception as exc:
        return show("Premium dashboard UI content is present", False, str(exc))


def verify_backend_routes_preserved() -> bool:
    try:
        from backend.main import app

        routes = {route.path for route in app.routes}
        expected = {
            "/dashboard/status",
            "/dashboard/overview",
            "/dashboard/cards",
            "/dashboard/summary",
            "/monitoring/alerts",
            "/brokers/status",
            "/accounts/status",
            "/execution-queue/status",
            "/phase3/status",
        }
        return show("Backend routes remain registered", expected <= routes)
    except Exception as exc:
        return show("Backend routes remain registered", False, str(exc))


def verify_safety() -> bool:
    try:
        source_suffixes = {".py", ".ts", ".tsx", ".js", ".jsx"}
        source_text = "\n".join(
            path.read_text(encoding="utf-8", errors="ignore")
            for root in ("backend", "frontend")
            for path in (PROJECT_ROOT / root).rglob("*")
            if path.is_file()
            and path.suffix in source_suffixes
            and "node_modules" not in path.parts
            and ".next" not in path.parts
        )
        passed = (
            "mt5.order_send" not in source_text
            and "order_send(" not in source_text
            and "live_execution_enabled=True" not in source_text
            and "real_trading_enabled=True" not in source_text
            and "enable_live_trading" not in source_text
        )
        return show("No live execution patterns were added", passed)
    except Exception as exc:
        return show("No live execution patterns were added", False, str(exc))


def main() -> int:
    print("Phase 4 Day 3 Premium Dashboard Verification")
    print("=" * 52)
    checks = [
        verify_files(),
        verify_api_helper(),
        verify_ui_content(),
        verify_backend_routes_preserved(),
        verify_safety(),
    ]
    print("=" * 52)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
