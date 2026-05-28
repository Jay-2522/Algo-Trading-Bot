import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def verify_live_panel_files() -> bool:
    files = [
        "frontend/components/dashboard/LiveBrokerPanel.tsx",
        "frontend/components/dashboard/LiveAccountRoutingPanel.tsx",
        "frontend/components/dashboard/LiveExecutionQueuePanel.tsx",
        "frontend/components/dashboard/LiveWebhookPanel.tsx",
        "frontend/components/dashboard/LiveMonitoringPanel.tsx",
        "frontend/components/dashboard/AutoRefreshControl.tsx",
        "frontend/hooks/useDashboardData.ts",
        "docs/phase-4-day-4-progress.md",
    ]
    return show("Live panel, auto-refresh hook, and documentation files exist", all((PROJECT_ROOT / path).is_file() for path in files))


def verify_api_helper_endpoints() -> bool:
    try:
        api = (PROJECT_ROOT / "frontend/lib/dashboard-api.ts").read_text(encoding="utf-8")
        expected = [
            "/dashboard/overview",
            "/dashboard/cards",
            "/monitoring/alerts",
            "/brokers/status",
            "/brokers/observation/status",
            "/accounts/status",
            "/accounts/allocation/status",
            "/execution-queue/status",
            "/execution-queue/lifecycle/status",
            "/webhooks/status",
            "/webhooks/orchestration/status",
            "/phase3/status",
        ]
        return show("Dashboard API helper includes all live data endpoints", all(endpoint in api for endpoint in expected))
    except Exception as exc:
        return show("Dashboard API helper includes all live data endpoints", False, str(exc))


def verify_shell_uses_live_panels_and_refresh() -> bool:
    try:
        shell = (PROJECT_ROOT / "frontend/components/dashboard/DashboardShell.tsx").read_text(encoding="utf-8")
        hook = (PROJECT_ROOT / "frontend/hooks/useDashboardData.ts").read_text(encoding="utf-8")
        control = (PROJECT_ROOT / "frontend/components/dashboard/AutoRefreshControl.tsx").read_text(encoding="utf-8")
        passed = (
            "LiveBrokerPanel" in shell
            and "LiveAccountRoutingPanel" in shell
            and "LiveExecutionQueuePanel" in shell
            and "LiveWebhookPanel" in shell
            and "LiveMonitoringPanel" in shell
            and "AutoRefreshControl" in shell
            and "useDashboardData(10000)" in shell
            and "setInterval" in hook
            and "requestInFlight" in hook
            and "previous" in hook
            and "Pause Auto" in control
            and "Resume Auto" in control
        )
        return show("Dashboard shell uses live panels and safe auto-refresh", passed)
    except Exception as exc:
        return show("Dashboard shell uses live panels and safe auto-refresh", False, str(exc))


def verify_day3_files_preserved() -> bool:
    files = [
        "frontend/components/dashboard/DashboardHeader.tsx",
        "frontend/components/dashboard/BrokerStatusPanel.tsx",
        "frontend/components/dashboard/AccountStatusPanel.tsx",
        "frontend/components/dashboard/ExecutionSafetyPanel.tsx",
        "frontend/components/dashboard/StatusBadge.tsx",
    ]
    return show("Day 3 premium dashboard polish files are preserved", all((PROJECT_ROOT / path).is_file() for path in files))


def verify_backend_routes_preserved() -> bool:
    try:
        from backend.main import app

        routes = {route.path for route in app.routes}
        expected = {
            "/dashboard/overview",
            "/dashboard/cards",
            "/monitoring/alerts",
            "/brokers/status",
            "/brokers/observation/status",
            "/accounts/status",
            "/accounts/allocation/status",
            "/execution-queue/status",
            "/execution-queue/lifecycle/status",
            "/webhooks/status",
            "/webhooks/orchestration/status",
            "/phase3/status",
        }
        return show("Backend live data routes remain registered", expected <= routes)
    except Exception as exc:
        return show("Backend live data routes remain registered", False, str(exc))


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
            and "real_trading_enabled=True" not in text
            and "enable_live_trading" not in text
        )
        return show("No live execution patterns were added", passed)
    except Exception as exc:
        return show("No live execution patterns were added", False, str(exc))


def main() -> int:
    print("Phase 4 Day 4 Real-Time Dashboard Verification")
    print("=" * 55)
    checks = [
        verify_live_panel_files(),
        verify_api_helper_endpoints(),
        verify_shell_uses_live_panels_and_refresh(),
        verify_day3_files_preserved(),
        verify_backend_routes_preserved(),
        verify_safety(),
    ]
    print("=" * 55)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
