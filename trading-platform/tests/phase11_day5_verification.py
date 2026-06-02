import re
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
        "backend/client_analytics/account_models.py",
        "backend/client_analytics/account_analytics_service.py",
        "backend/client_analytics/account_snapshot_store.py",
        "frontend/components/account-analytics/AccountAnalyticsSection.tsx",
        "frontend/components/account-analytics/AccountOverviewCards.tsx",
        "frontend/components/account-analytics/AccountPerformanceGrid.tsx",
        "frontend/components/account-analytics/CopierSyncPanel.tsx",
        "frontend/components/account-analytics/AccountAnalyticsEmptyState.tsx",
        "frontend/lib/accountAnalyticsApi.ts",
        "docs/phase-11-day-5-progress.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    return show("Account analytics backend, frontend, API client, and docs exist", not missing, ", ".join(missing))


def verify_account_routes() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        accounts = client.get("/client-analytics/accounts")
        master = client.get("/client-analytics/accounts/master")
        copiers = client.get("/client-analytics/accounts/copiers")
        sync = client.get("/client-analytics/accounts/sync-status")
        account = client.get("/client-analytics/accounts/STARTRADER_DEMO_1")
        accounts_payload = accounts.json()
        master_payload = master.json()
        copiers_payload = copiers.json()
        sync_payload = sync.json()
        passed = (
            accounts.status_code == 200
            and master.status_code == 200
            and copiers.status_code == 200
            and sync.status_code == 200
            and account.status_code == 200
            and len(accounts_payload) >= 4
            and master_payload["account_type"] == "MASTER"
            and len(copiers_payload) == 3
            and sync_payload["simulation_only"] is True
            and sync_payload["demo_execution"] is True
            and sync_payload["live_execution_enabled"] is False
            and sync_payload["broker_execution_enabled"] is False
            and all(item["net_pnl"] == 0.0 for item in accounts_payload)
            and all(item["simulation_only"] is True for item in accounts_payload)
            and all(item["demo_execution"] is True for item in accounts_payload)
            and all(item["live_execution_enabled"] is False for item in accounts_payload)
            and all(item["broker_execution_enabled"] is False for item in accounts_payload)
        )
        return show("Account analytics endpoints work with safety flags and no fake PnL", passed)
    except Exception as exc:
        return show("Account analytics endpoints work with safety flags and no fake PnL", False, str(exc))


def verify_dashboard_account_ui() -> bool:
    try:
        page = (PROJECT_ROOT / "frontend" / "app" / "dashboard" / "page.tsx").read_text(encoding="utf-8")
        section = (PROJECT_ROOT / "frontend" / "components" / "account-analytics" / "AccountAnalyticsSection.tsx").read_text(encoding="utf-8")
        grid = (PROJECT_ROOT / "frontend" / "components" / "account-analytics" / "AccountPerformanceGrid.tsx").read_text(encoding="utf-8")
        sync = (PROJECT_ROOT / "frontend" / "components" / "account-analytics" / "CopierSyncPanel.tsx").read_text(encoding="utf-8")
        passed = (
            "AccountAnalyticsSection" in page
            and "Account Analytics & Copier Intelligence" in section
            and "SIMULATION ONLY" in section
            and "LIVE DISABLED" in section
            and "Net P&L" in grid
            and "Synchronization Monitoring" in sync
        )
        return show("Account analytics dashboard section, grid, and sync panel exist", passed)
    except Exception as exc:
        return show("Account analytics dashboard section, grid, and sync panel exist", False, str(exc))


def verify_no_fake_pnl_and_order_send() -> bool:
    try:
        paths = [
            *list((PROJECT_ROOT / "frontend" / "components" / "account-analytics").glob("*.tsx")),
            PROJECT_ROOT / "frontend" / "lib" / "accountAnalyticsApi.ts",
            *list((PROJECT_ROOT / "backend" / "client_analytics").glob("account*.py")),
        ]
        suspicious: list[str] = []
        fake_profit_pattern = re.compile(r"[\+\$]\s?(?:[1-9]\d{2,}|900|1000|5000)")
        for path in paths:
            text = path.read_text(encoding="utf-8")
            for match in fake_profit_pattern.finditer(text):
                snippet = text[max(0, match.start() - 30) : match.end() + 30]
                if "Number(" in snippet or "net_pnl" in snippet or "money(" in snippet:
                    continue
                suspicious.append(f"{path.name}: {match.group(0)}")
        token = "mt5." + "order_send"
        matches = []
        for path in (PROJECT_ROOT / "backend").rglob("*.py"):
            if path.is_file() and token in path.read_text(encoding="utf-8", errors="ignore"):
                matches.append(path.relative_to(PROJECT_ROOT).as_posix())
        passed = not suspicious and matches == ["backend/demo_execution/mt5_demo_executor.py"]
        return show("No fake PnL strings and no new mt5.order_send exist", passed, ", ".join(suspicious + matches))
    except Exception as exc:
        return show("No fake PnL strings and no new mt5.order_send exist", False, str(exc))


def verify_phase11_routes_preserved() -> bool:
    try:
        from backend.main import app

        required = {
            "/client-analytics/status",
            "/client-analytics/overview",
            "/client-analytics/symbols",
            "/client-analytics/sessions",
            "/client-analytics/risk",
            "/client-analytics/snapshots/latest",
            "/client-analytics/reports/status",
            "/client-analytics/reports/daily",
            "/client-analytics/accounts",
            "/client-analytics/accounts/master",
            "/client-analytics/accounts/copiers",
            "/client-analytics/accounts/sync-status",
            "/client-analytics/accounts/{account_id}",
        }
        registered = {route.path for route in app.routes if hasattr(route, "methods") and "GET" in route.methods}
        return show("Phase 11 Day 1-4 and account routes are preserved", required <= registered)
    except Exception as exc:
        return show("Phase 11 Day 1-4 and account routes are preserved", False, str(exc))


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
    print("Phase 11 Day 5 Account-Level Analytics & Multi-Account Reporting Verification")
    print("=" * 78)
    checks = [
        verify_files(),
        verify_account_routes(),
        verify_dashboard_account_ui(),
        verify_no_fake_pnl_and_order_send(),
        verify_phase11_routes_preserved(),
        verify_frontend_build(),
    ]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
