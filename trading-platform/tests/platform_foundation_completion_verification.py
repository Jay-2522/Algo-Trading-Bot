import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

TRADE_JOURNAL_ROUTES = {
    "/trade-journal/persistence/status",
    "/trade-journal/persistence/planned",
    "/trade-journal/persistence/order-sent",
    "/trade-journal/persistence/order-rejected",
    "/trade-journal/persistence/trade-opened",
    "/trade-journal/persistence/trade-closed",
    "/trade-journal/persistence/recent",
    "/trade-journal/persistence/summary",
    "/trade-journal/persistence/{trade_id}",
}

STRATEGY_DASHBOARD_ROUTES = {
    "/client-analytics/strategy-dashboard/status",
    "/client-analytics/strategy-dashboard/overview",
    "/client-analytics/strategy-dashboard/symbols",
    "/client-analytics/strategy-dashboard/rejections",
    "/client-analytics/strategy-dashboard/performance",
}

REPORTS_V2_ROUTES = {
    "/client-analytics/reports-v2/status",
    "/client-analytics/reports-v2/daily",
    "/client-analytics/reports-v2/weekly",
    "/client-analytics/reports-v2/monthly",
    "/client-analytics/reports-v2/symbol/{symbol}",
    "/client-analytics/reports-v2/export/json",
    "/client-analytics/reports-v2/export/csv",
}

TRADE_COPIER_ROUTES = {
    "/trade-copier/status",
    "/trade-copier/master-signal/create",
    "/trade-copier/queue/simulate",
    "/trade-copier/queue",
    "/trade-copier/accounts",
    "/trade-copier/batches",
    "/trade-copier/readiness",
}


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def walk(payload: Any):
    if isinstance(payload, dict):
        for key, value in payload.items():
            yield key, value
            yield from walk(value)
    elif isinstance(payload, list):
        for item in payload:
            yield from walk(item)


def safety_ok(payload: Any) -> bool:
    for key, value in walk(payload):
        if key in {"live_execution_enabled", "broker_execution_enabled", "execution_allowed"} and value is not False:
            return False
        if key == "simulation_only" and value is not True:
            return False
    return True


def route_paths(app) -> set[str]:
    return {route.path for route in app.routes if hasattr(route, "methods")}


def verify_files_and_routes(client: TestClient, app) -> bool:
    files = [
        "backend/trade_journal/persistent_trade_journal_service.py",
        "backend/api/trade_journal_persistence_routes.py",
        "backend/client_analytics/reporting_engine_service.py",
        "backend/trade_copier/copier_models.py",
        "backend/trade_copier/copier_service.py",
        "docs/phase18-controlled-demo-trade-monitoring-plan.md",
        "docs/phase18-roadmap.md",
    ]
    missing_files = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    missing_routes = sorted((TRADE_JOURNAL_ROUTES | STRATEGY_DASHBOARD_ROUTES | REPORTS_V2_ROUTES | TRADE_COPIER_ROUTES) - route_paths(app))
    status_checks = [
        client.get("/trade-journal/persistence/status"),
        client.get("/client-analytics/strategy-dashboard/status"),
        client.get("/client-analytics/reports-v2/status"),
        client.get("/trade-copier/status"),
    ]
    passed = not missing_files and not missing_routes and all(response.status_code == 200 for response in status_checks)
    return show("Platform foundation files and routes exist", passed, ", ".join(missing_files + missing_routes))


def verify_trade_journal_summary_and_empty_state() -> bool:
    try:
        from backend.trade_journal.persistent_trade_journal_service import PersistentTradeJournalService

        with TemporaryDirectory() as tmp:
            service = PersistentTradeJournalService(Path(tmp) / "trade_journal.json")
            summary = service.get_summary()
            passed = (
                summary["total_trades"] == 0
                and summary["closed_demo_trades"] == 0
                and summary["win_rate"] == 0.0
                and summary["net_pnl"] == 0.0
                and summary["empty_state"] is True
                and "No completed demo trades yet." in summary["message"]
                and safety_ok(summary)
            )
            return show("Empty persistent journal does not fake trades", passed, str(summary))
    except Exception as exc:
        return show("Empty persistent journal does not fake trades", False, str(exc))


def verify_reports_and_csv(client: TestClient) -> bool:
    daily = client.get("/client-analytics/reports-v2/daily")
    csv_response = client.get("/client-analytics/reports-v2/export/csv")
    csv_text = csv_response.text
    passed = (
        daily.status_code == 200
        and csv_response.status_code == 200
        and "report_id,report_type,period,symbol,total_trades,closed_demo_trades,win_rate,net_pnl,avg_rr,generated_at" in csv_text
        and safety_ok(daily.json())
    )
    return show("Reports V2 and CSV export work with empty data", passed, csv_text.splitlines()[0] if csv_text else "")


def verify_strategy_dashboard(client: TestClient) -> bool:
    overview = client.get("/client-analytics/strategy-dashboard/overview")
    symbols = client.get("/client-analytics/strategy-dashboard/symbols")
    rejections = client.get("/client-analytics/strategy-dashboard/rejections")
    performance = client.get("/client-analytics/strategy-dashboard/performance")
    payloads = [overview.json(), symbols.json(), rejections.json(), performance.json()]
    passed = (
        all(response.status_code == 200 for response in [overview, symbols, rejections, performance])
        and overview.json().get("live_execution_enabled") is False
        and performance.json().get("net_pnl", 0) == 0
        and all(safety_ok(payload) for payload in payloads)
    )
    return show("Strategy analytics dashboard routes are safe", passed)


def verify_trade_copier_simulation(client: TestClient) -> bool:
    simulate = client.post("/trade-copier/queue/simulate", json={"symbol": "EURUSD", "side": "BUY", "lot": 0.01})
    readiness = client.get("/trade-copier/readiness")
    queue = client.get("/trade-copier/queue")
    payloads = [simulate.json(), readiness.json(), queue.json()]
    passed = (
        simulate.status_code == 200
        and readiness.status_code == 200
        and queue.status_code == 200
        and simulate.json().get("simulation_only") is True
        and readiness.json().get("execution_allowed") is False
        and readiness.json().get("mt5_order_send_used") is False
        and all(safety_ok(payload) for payload in payloads)
    )
    return show("Trade copier simulation does not execute", passed)


def verify_no_new_order_send() -> bool:
    token = "mt5." + "order_send"
    allowed = [
        "backend/demo_execution/mt5_demo_executor.py",
        "backend/mt5_demo/guarded_demo_order_sender_service.py",
    ]
    matches = [
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in (PROJECT_ROOT / "backend").rglob("*.py")
        if token in path.read_text(encoding="utf-8", errors="ignore")
    ]
    return show("No new unrestricted mt5.order_send path exists", sorted(matches) == allowed, ", ".join(matches))


def verify_frontend_build_script() -> bool:
    package_json = (PROJECT_ROOT / "frontend" / "package.json").read_text(encoding="utf-8")
    return show("Frontend build is verified separately by npm run build", '"build": "next build"' in package_json)


def main() -> int:
    print("Platform Foundation Completion Verification")
    print("=" * 78)
    try:
        from backend.main import app
    except Exception as exc:
        show("Import backend.main app", False, str(exc))
        print("=" * 78)
        print("FAIL")
        return 1

    with TestClient(app) as client:
        checks = [
            verify_files_and_routes(client, app),
            verify_trade_journal_summary_and_empty_state(),
            verify_strategy_dashboard(client),
            verify_reports_and_csv(client),
            verify_trade_copier_simulation(client),
            verify_no_new_order_send(),
            verify_frontend_build_script(),
        ]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
