import re
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def verify_files() -> bool:
    files = [
        "frontend/components/client-analytics/ClientAnalyticsSection.tsx",
        "frontend/components/client-analytics/AnalyticsOverviewCards.tsx",
        "frontend/components/client-analytics/SymbolPerformanceGrid.tsx",
        "frontend/components/client-analytics/SessionPerformancePanel.tsx",
        "frontend/components/client-analytics/RiskAnalyticsPanel.tsx",
        "frontend/components/client-analytics/AnalyticsEmptyState.tsx",
        "frontend/lib/clientAnalyticsApi.ts",
        "docs/phase-11-day-2-progress.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    return show("Client analytics UI files and API client exist", not missing, ", ".join(missing))


def verify_dashboard_integration_and_labels() -> bool:
    try:
        page = (PROJECT_ROOT / "frontend" / "app" / "dashboard" / "page.tsx").read_text(encoding="utf-8")
        section = (PROJECT_ROOT / "frontend" / "components" / "client-analytics" / "ClientAnalyticsSection.tsx").read_text(encoding="utf-8")
        symbol_grid = (PROJECT_ROOT / "frontend" / "components" / "client-analytics" / "SymbolPerformanceGrid.tsx").read_text(encoding="utf-8")
        passed = (
            "ClientAnalyticsSection" in page
            and "Client Analytics & Performance Intelligence" in section
            and "SIMULATION ONLY" in section
            and "DEMO MODE" in section
            and "LIVE DISABLED" in section
            and "simulation_only" in section
            and "live_execution_enabled" in section
            and "broker_execution_enabled" in section
            and "Placeholder / Pending Indian Broker Integration" in symbol_grid
        )
        return show("Dashboard imports analytics section and safety/NIFTY50 labels exist", passed)
    except Exception as exc:
        return show("Dashboard imports analytics section and safety/NIFTY50 labels exist", False, str(exc))


def verify_no_fake_pnl_strings() -> bool:
    try:
        paths = [
            *list((PROJECT_ROOT / "frontend" / "components" / "client-analytics").glob("*.tsx")),
            PROJECT_ROOT / "frontend" / "lib" / "clientAnalyticsApi.ts",
        ]
        suspicious: list[str] = []
        fake_profit_pattern = re.compile(r"[\+\$]\s?(?:[1-9]\d{2,}|900|1000|5000)")
        for path in paths:
            text = path.read_text(encoding="utf-8")
            for match in fake_profit_pattern.finditer(text):
                snippet = text[max(0, match.start() - 20) : match.end() + 20]
                if "formatMoney" in snippet or "Number(value" in snippet:
                    continue
                suspicious.append(f"{path.name}: {match.group(0)}")
        return show("No hardcoded fake PnL strings are present in analytics UI", not suspicious, ", ".join(suspicious))
    except Exception as exc:
        return show("No hardcoded fake PnL strings are present in analytics UI", False, str(exc))


def verify_backend_routes_preserved() -> bool:
    try:
        from backend.main import app

        required = {
            "/client-analytics/status",
            "/client-analytics/overview",
            "/client-analytics/symbols",
            "/client-analytics/sessions",
            "/client-analytics/risk",
            "/client-analytics/snapshots/latest",
        }
        registered = {route.path for route in app.routes if hasattr(route, "methods") and "GET" in route.methods}
        return show("Phase 11 Day 1 backend analytics routes are preserved", required <= registered)
    except Exception as exc:
        return show("Phase 11 Day 1 backend analytics routes are preserved", False, str(exc))


def verify_order_send_safety() -> bool:
    token = "mt5." + "order_send"
    matches = []
    for path in (PROJECT_ROOT / "backend").rglob("*.py"):
        if path.is_file() and token in path.read_text(encoding="utf-8", errors="ignore"):
            matches.append(path.relative_to(PROJECT_ROOT).as_posix())
    return show("No new mt5.order_send was added", matches == ["backend/demo_execution/mt5_demo_executor.py"], ", ".join(matches))


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
    print("Phase 11 Day 2 Client Dashboard Analytics UI Verification")
    print("=" * 64)
    checks = [
        verify_files(),
        verify_dashboard_integration_and_labels(),
        verify_no_fake_pnl_strings(),
        verify_backend_routes_preserved(),
        verify_order_send_safety(),
        verify_frontend_build(),
    ]
    print("=" * 64)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
