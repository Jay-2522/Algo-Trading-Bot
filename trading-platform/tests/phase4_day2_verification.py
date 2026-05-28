import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def verify_frontend_files() -> bool:
    files = [
        "frontend/app/dashboard/page.tsx",
        "frontend/components/dashboard/DashboardShell.tsx",
        "frontend/components/dashboard/DashboardCard.tsx",
        "frontend/components/dashboard/DashboardStatusGrid.tsx",
        "frontend/components/dashboard/DashboardAlertsPanel.tsx",
        "frontend/components/dashboard/DashboardSafetyBanner.tsx",
        "frontend/lib/dashboard-api.ts",
        "docs/phase-4-day-2-progress.md",
    ]
    files_ok = all((PROJECT_ROOT / path).is_file() for path in files)
    return show("Dashboard frontend files and documentation exist", files_ok)


def verify_frontend_content() -> bool:
    try:
        shell = (PROJECT_ROOT / "frontend/components/dashboard/DashboardShell.tsx").read_text(encoding="utf-8")
        banner = (PROJECT_ROOT / "frontend/components/dashboard/DashboardSafetyBanner.tsx").read_text(encoding="utf-8")
        api = (PROJECT_ROOT / "frontend/lib/dashboard-api.ts").read_text(encoding="utf-8")
        page = (PROJECT_ROOT / "frontend/app/dashboard/page.tsx").read_text(encoding="utf-8")
        passed = (
            "AI Multi-Market Trading Bot" in shell
            and "VPS Dashboard &amp; Simulation Control Center" in shell
            and "Refresh" in shell
            and "setInterval" in shell
            and "Simulation Only" in banner
            and "Live Execution" in banner
            and "Broker Orders" in banner
            and "/dashboard/status" in api
            and "/dashboard/overview" in api
            and "/dashboard/cards" in api
            and "/dashboard/summary" in api
            and "/monitoring/alerts" in api
            and "DashboardShell" in page
        )
        return show("Dashboard frontend shell contains required sections and API integration", passed)
    except Exception as exc:
        return show("Dashboard frontend shell contains required sections and API integration", False, str(exc))


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
            "/phase3/status",
        }
        return show("Backend dashboard, monitoring, and Phase 3 routes remain registered", expected <= routes)
    except Exception as exc:
        return show("Backend dashboard, monitoring, and Phase 3 routes remain registered", False, str(exc))


def verify_safety() -> bool:
    try:
        source_suffixes = {".py", ".ts", ".tsx", ".js", ".jsx"}
        backend_text = "\n".join(
            path.read_text(encoding="utf-8", errors="ignore")
            for path in (PROJECT_ROOT / "backend").rglob("*.py")
        )
        frontend_text = "\n".join(
            path.read_text(encoding="utf-8", errors="ignore")
            for path in (PROJECT_ROOT / "frontend").rglob("*")
            if path.is_file()
            and path.suffix in source_suffixes
            and "node_modules" not in path.parts
            and ".next" not in path.parts
        )
        passed = (
            "mt5.order_send" not in backend_text
            and "order_send(" not in backend_text
            and "live_execution_enabled=True" not in backend_text
            and "mt5.order_send" not in frontend_text
            and "order_send(" not in frontend_text
            and "live_execution_enabled=True" not in frontend_text
        )
        return show("No live execution patterns were added", passed)
    except Exception as exc:
        return show("No live execution patterns were added", False, str(exc))


def main() -> int:
    print("Phase 4 Day 2 VPS Dashboard Frontend Verification")
    print("=" * 56)
    checks = [
        verify_frontend_files(),
        verify_frontend_content(),
        verify_backend_routes_preserved(),
        verify_safety(),
    ]
    print("=" * 56)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
