import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

SERVICE_PATH = PROJECT_ROOT / "backend/analytics/trade_outcome_intelligence_service.py"
DASHBOARD_PATH = PROJECT_ROOT / "frontend/components/dashboard/DashboardShell.tsx"

ROUTES = {
    "/analytics/outcomes/status",
    "/analytics/outcomes/latest",
    "/analytics/outcomes/trades",
    "/analytics/outcomes/symbols",
    "/analytics/outcomes/sessions",
    "/analytics/outcomes/summary",
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
        if key in {"live_execution_enabled", "broker_execution_enabled", "execution_allowed", "mt5_order_send_used"} and value is not False:
            return False
    return True


def closed_trade(ticket: str, result: str, pnl: float, symbol: str, side: str, exit_reason: str, opened_at: str) -> dict[str, Any]:
    return {
        "trade_id": f"mt5_demo_{ticket}",
        "source": "MT5_DEMO",
        "environment": "DEMO",
        "symbol": symbol,
        "side": side,
        "lot": 0.01,
        "entry_price": 1.1,
        "stop_loss": 1.095,
        "take_profit": 1.11,
        "risk_reward_ratio": 2.0,
        "mt5_ticket": ticket,
        "opened_at": opened_at,
        "closed_at": "2026-06-08T13:15:00+00:00",
        "close_price": 1.11 if result == "WIN" else 1.095 if result == "LOSS" else 1.1,
        "profit_loss": pnl,
        "net_pnl": pnl,
        "realized_pnl": pnl,
        "duration_minutes": 75,
        "exit_reason": exit_reason,
        "result": result,
        "notes": "sample closed trade",
    }


def seed_journal(journal) -> None:
    journal.record_trade_closed(closed_trade("1", "WIN", 3.0, "EURUSD", "BUY", "TAKE_PROFIT", "2026-06-08T08:00:00+00:00"))
    journal.record_trade_closed(closed_trade("2", "LOSS", -1.5, "EURUSD", "SELL", "STOP_LOSS", "2026-06-08T13:00:00+00:00"))
    journal.record_trade_closed(closed_trade("3", "BREAKEVEN", 0.0, "XAUUSD", "BUY", "MANUAL", "2026-06-08T01:00:00+00:00"))


def verify_routes_exist() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        paths = {route.path for route in app.routes if hasattr(route, "methods")}
        missing = sorted(ROUTES - paths)
        status = client.get("/analytics/outcomes/status")
        passed = not missing and status.status_code == 200 and safety_ok(status.json())
        return show("Outcome analytics routes exist", passed, ", ".join(missing))
    except Exception as exc:
        return show("Outcome analytics routes exist", False, str(exc))


def verify_attribution_and_aggregation() -> bool:
    try:
        from backend.analytics.trade_outcome_intelligence_service import TradeOutcomeIntelligenceService
        from backend.trade_journal.persistent_trade_journal_service import PersistentTradeJournalService

        with TemporaryDirectory() as tmp:
            journal = PersistentTradeJournalService(Path(tmp) / "trade_journal.json")
            seed_journal(journal)
            service = TradeOutcomeIntelligenceService(journal)
            trades = service.get_trades()
            summary = service.get_summary()
            symbols = service.get_symbol_performance()
            sessions = service.get_session_performance()
            by_ticket = {trade["mt5_ticket"]: trade for trade in trades}
            eurusd = next(item for item in symbols if item["symbol"] == "EURUSD")
            passed = (
                len(trades) == 3
                and by_ticket["1"]["outcome_attribution"] == "TP reached"
                and by_ticket["2"]["outcome_attribution"] == "SL reached"
                and by_ticket["3"]["outcome_attribution"] == "minimal pnl"
                and by_ticket["1"]["realized_rr"] is not None
                and summary["total_closed_trades"] == 3
                and summary["wins"] == 1
                and summary["losses"] == 1
                and summary["breakeven"] == 1
                and summary["win_rate"] == 33.33
                and summary["net_pnl"] == 1.5
                and summary["avg_rr"] != 0
                and summary["best_trade"]["mt5_ticket"] == "1"
                and summary["worst_trade"]["mt5_ticket"] == "2"
                and summary["best_symbol"] == "EURUSD"
                and eurusd["total_trades"] == 2
                and eurusd["net_pnl"] == 1.5
                and len(sessions) >= 2
                and safety_ok(summary)
                and safety_ok(symbols)
                and safety_ok(sessions)
            )
            return show("Attribution and performance aggregation work", passed, str({"summary": summary, "symbols": symbols, "sessions": sessions}))
    except Exception as exc:
        return show("Attribution and performance aggregation work", False, str(exc))


def verify_empty_state_no_fake_data() -> bool:
    try:
        from backend.analytics.trade_outcome_intelligence_service import TradeOutcomeIntelligenceService
        from backend.trade_journal.persistent_trade_journal_service import PersistentTradeJournalService

        with TemporaryDirectory() as tmp:
            service = TradeOutcomeIntelligenceService(PersistentTradeJournalService(Path(tmp) / "trade_journal.json"))
            summary = service.get_summary()
            passed = summary["total_closed_trades"] == 0 and summary["net_pnl"] == 0.0 and summary["empty_state"] is True and service.get_trades() == [] and safety_ok(summary)
            return show("Empty closed-trade state does not fake analytics", passed, str(summary))
    except Exception as exc:
        return show("Empty closed-trade state does not fake analytics", False, str(exc))


def verify_reports_v3() -> bool:
    try:
        from backend.client_analytics.reporting_engine_service import ReportingEngineService
        from backend.trade_journal.persistent_trade_journal_service import PersistentTradeJournalService

        with TemporaryDirectory() as tmp:
            journal = PersistentTradeJournalService(Path(tmp) / "trade_journal.json")
            seed_journal(journal)
            report = ReportingEngineService(journal).build_performance_v3()
            passed = (
                report["performance_summary"]["total_closed_trades"] == 3
                and len(report["symbol_breakdown"]) == 2
                and len(report["session_breakdown"]) >= 2
                and report["outcome_attribution_summary"]["TP reached"] == 1
                and report["empty_state"] is False
                and safety_ok(report)
            )
            return show("Reports V3 performance builds from outcome intelligence", passed, str(report))
    except Exception as exc:
        return show("Reports V3 performance builds from outcome intelligence", False, str(exc))


def verify_dashboard_metrics_exist() -> bool:
    text = DASHBOARD_PATH.read_text(encoding="utf-8")
    required = ["DEMO Performance", "Trade Outcome Intelligence", "/analytics/outcomes/summary", "Total Closed Trades", "Best Symbol", "Worst Symbol"]
    missing = [token for token in required if token not in text]
    return show("Dashboard displays outcome metrics", not missing, ", ".join(missing))


def verify_no_execution_logic() -> bool:
    service_text = SERVICE_PATH.read_text(encoding="utf-8")
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
    forbidden = ["mt5.order_send", "order_send(", "position_close", "close_order", "live_execution_enabled=True", "broker_execution_enabled=True"]
    present = [item for item in forbidden if item in service_text]
    return show("No execution logic changed or added", not present and sorted(matches) == allowed, ", ".join(present + matches))


def main() -> int:
    print("Phase 18 Day 5 Outcome Intelligence Verification")
    print("=" * 78)
    checks = [
        verify_routes_exist(),
        verify_attribution_and_aggregation(),
        verify_empty_state_no_fake_data(),
        verify_reports_v3(),
        verify_dashboard_metrics_exist(),
        verify_no_execution_logic(),
    ]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
