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
        "backend/client_analytics/report_models.py",
        "backend/client_analytics/report_builder.py",
        "backend/client_analytics/export_service.py",
        "backend/client_analytics/report_store.py",
        "frontend/components/reports/ClientReportsSection.tsx",
        "frontend/components/reports/ReportSummaryCards.tsx",
        "frontend/components/reports/ReportExportPanel.tsx",
        "frontend/components/reports/ReportPreview.tsx",
        "frontend/components/reports/ReportEmptyState.tsx",
        "frontend/lib/clientReportsApi.ts",
        "docs/phase-11-day-4-progress.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    return show("Report backend, frontend, docs, and API client files exist", not missing, ", ".join(missing))


def verify_report_routes() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        required = [
            "/client-analytics/reports/status",
            "/client-analytics/reports/daily",
            "/client-analytics/reports/weekly",
            "/client-analytics/reports/symbol/XAUUSD",
            "/client-analytics/reports/risk",
            "/client-analytics/reports/trade-journal",
            "/client-analytics/reports/export/json",
            "/client-analytics/reports/export/csv",
        ]
        responses = {route: client.get(route) for route in required}
        daily = responses["/client-analytics/reports/daily"].json()
        weekly = responses["/client-analytics/reports/weekly"].json()
        symbol = responses["/client-analytics/reports/symbol/XAUUSD"].json()
        risk = responses["/client-analytics/reports/risk"].json()
        json_export = responses["/client-analytics/reports/export/json"].json()
        csv_export = responses["/client-analytics/reports/export/csv"].text
        passed = (
            all(response.status_code == 200 for response in responses.values())
            and daily["report_type"] == "DAILY"
            and weekly["report_type"] == "WEEKLY"
            and symbol["report_type"] == "SYMBOL"
            and risk["report_type"] == "RISK"
            and json_export["simulation_only"] is True
            and daily["simulation_only"] is True
            and daily["demo_execution"] is True
            and daily["live_execution_enabled"] is False
            and daily["broker_execution_enabled"] is False
            and "report_id,report_type,period,symbol,total_signals,demo_executions,win_rate,net_pnl" in csv_export
        )
        return show("Report routes, JSON export, CSV export, and safety flags work", passed)
    except Exception as exc:
        return show("Report routes, JSON export, CSV export, and safety flags work", False, str(exc))


def verify_dashboard_reports_ui() -> bool:
    try:
        page = (PROJECT_ROOT / "frontend" / "app" / "dashboard" / "page.tsx").read_text(encoding="utf-8")
        section = (PROJECT_ROOT / "frontend" / "components" / "reports" / "ClientReportsSection.tsx").read_text(encoding="utf-8")
        export_panel = (PROJECT_ROOT / "frontend" / "components" / "reports" / "ReportExportPanel.tsx").read_text(encoding="utf-8")
        preview = (PROJECT_ROOT / "frontend" / "components" / "reports" / "ReportPreview.tsx").read_text(encoding="utf-8")
        passed = (
            "ClientReportsSection" in page
            and "Client Reports & Exports" in section
            and "DEMO REPORT" in section
            and "SIMULATION ONLY" in section
            and "LIVE DISABLED" in section
            and "Export JSON" in export_panel
            and "Export CSV" in export_panel
            and "Print Report" in export_panel
            and "Printable Report View" in preview
        )
        return show("Reports UI, export panel, printable preview, and labels exist", passed)
    except Exception as exc:
        return show("Reports UI, export panel, printable preview, and labels exist", False, str(exc))


def verify_no_fake_pnl_and_order_send() -> bool:
    try:
        paths = [
            *list((PROJECT_ROOT / "frontend" / "components" / "reports").glob("*.tsx")),
            PROJECT_ROOT / "frontend" / "lib" / "clientReportsApi.ts",
            *list((PROJECT_ROOT / "backend" / "client_analytics").glob("report*.py")),
            PROJECT_ROOT / "backend" / "client_analytics" / "export_service.py",
        ]
        suspicious: list[str] = []
        fake_profit_pattern = re.compile(r"[\+\$]\s?(?:[1-9]\d{2,}|900|1000|5000)")
        for path in paths:
            text = path.read_text(encoding="utf-8")
            for match in fake_profit_pattern.finditer(text):
                snippet = text[max(0, match.start() - 30) : match.end() + 30]
                if "Number(" in snippet or "net_pnl" in snippet:
                    continue
                suspicious.append(f"{path.name}: {match.group(0)}")
        token = "mt5." + "order_send"
        matches = []
        for path in (PROJECT_ROOT / "backend").rglob("*.py"):
            if path.is_file() and token in path.read_text(encoding="utf-8", errors="ignore"):
                matches.append(path.relative_to(PROJECT_ROOT).as_posix())
        passed = not suspicious and matches == ["backend/demo_execution/mt5_demo_executor.py"]
        return show("No fake PnL/report strings and no new mt5.order_send exist", passed, ", ".join(suspicious + matches))
    except Exception as exc:
        return show("No fake PnL/report strings and no new mt5.order_send exist", False, str(exc))


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
        }
        registered = {route.path for route in app.routes if hasattr(route, "methods") and "GET" in route.methods}
        return show("Phase 11 Day 1-3 routes are preserved", required <= registered)
    except Exception as exc:
        return show("Phase 11 Day 1-3 routes are preserved", False, str(exc))


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
    print("Phase 11 Day 4 Client Reporting & Export System Verification")
    print("=" * 68)
    checks = [
        verify_files(),
        verify_report_routes(),
        verify_dashboard_reports_ui(),
        verify_no_fake_pnl_and_order_send(),
        verify_phase11_routes_preserved(),
        verify_frontend_build(),
    ]
    print("=" * 68)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
