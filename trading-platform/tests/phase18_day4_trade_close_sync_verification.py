import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

CLOSE_SYNC_PATH = PROJECT_ROOT / "backend/mt5_demo/mt5_trade_close_sync_service.py"
DASHBOARD_PATH = PROJECT_ROOT / "frontend/components/dashboard/DashboardShell.tsx"

ROUTES = {
    "/mt5-demo/close-sync/status",
    "/mt5-demo/close-sync/run",
    "/mt5-demo/close-sync/latest",
    "/mt5-demo/close-sync/history",
    "/mt5-demo/close-sync/analytics",
}


class FakeMT5:
    ACCOUNT_TRADE_MODE_DEMO = 0
    DEAL_ENTRY_OUT = 1
    DEAL_ENTRY_OUT_BY = 3

    def __init__(self, positions: list[Any], deals: list[Any]) -> None:
        self.positions = positions
        self.deals = deals
        self.order_send_called = False

    def initialize(self) -> bool:
        return True

    def shutdown(self) -> None:
        return None

    def last_error(self) -> tuple[int, str]:
        return (0, "OK")

    def account_info(self) -> Any:
        return SimpleNamespace(login=123456, server="MetaQuotes-Demo", trade_mode=self.ACCOUNT_TRADE_MODE_DEMO)

    def positions_get(self) -> list[Any]:
        return self.positions

    def history_deals_get(self, _since: Any, _now: Any) -> list[Any]:
        return self.deals

    def history_orders_get(self, _since: Any, _now: Any) -> list[Any]:
        return []

    def order_send(self, _request: dict[str, Any]) -> None:
        self.order_send_called = True
        raise AssertionError("order_send must not be called by close sync")


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


def open_trade_payload(ticket: str = "8965515202") -> dict[str, Any]:
    return {
        "trade_id": f"mt5_demo_{ticket}",
        "source": "MT5_DEMO",
        "environment": "DEMO",
        "symbol": "EURUSD",
        "side": "BUY",
        "lot": 0.01,
        "entry_price": 1.15259,
        "stop_loss": 1.14973,
        "take_profit": 1.15573,
        "profit_loss": -0.79,
        "risk_reward_ratio": 2.0,
        "mt5_ticket": ticket,
        "account_login": "123456",
        "server": "MetaQuotes-Demo",
        "opened_at": "2026-06-08T07:58:58+00:00",
        "notes": "Synced from MT5 open position.",
    }


def open_position(ticket: int = 8965515202) -> Any:
    return SimpleNamespace(ticket=ticket, symbol="EURUSD", volume=0.01)


def close_deal(profit: float, price: float = 1.15573, ticket: int = 8965515202) -> Any:
    return SimpleNamespace(
        ticket=8584944743,
        order=8584944743,
        position_id=ticket,
        symbol="EURUSD",
        volume=0.01,
        price=price,
        profit=profit,
        swap=-0.1,
        commission=-0.04,
        time=1780917695,
        entry=1,
        comment="closed",
    )


def verify_routes_exist() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        paths = {route.path for route in app.routes if hasattr(route, "methods")}
        missing = sorted(ROUTES - paths)
        status = client.get("/mt5-demo/close-sync/status")
        analytics = client.get("/mt5-demo/close-sync/analytics")
        passed = not missing and status.status_code == 200 and analytics.status_code == 200 and safety_ok(status.json()) and safety_ok(analytics.json())
        return show("Close sync routes exist", passed, ", ".join(missing))
    except Exception as exc:
        return show("Close sync routes exist", False, str(exc))


def service_with_fake_mt5(journal, fake_mt5):
    from backend.mt5_demo import mt5_trade_close_sync_service as module
    from backend.mt5_demo.mt5_trade_close_sync_service import MT5TradeCloseSyncService

    old_mt5 = module.mt5
    module.mt5 = fake_mt5
    return MT5TradeCloseSyncService(journal), module, old_mt5


def verify_still_open_remains_open() -> bool:
    try:
        from backend.trade_journal.persistent_trade_journal_service import PersistentTradeJournalService

        with TemporaryDirectory() as tmp:
            journal = PersistentTradeJournalService(Path(tmp) / "trade_journal.json")
            journal.record_open_position(open_trade_payload())
            fake_mt5 = FakeMT5([open_position()], [close_deal(3.14)])
            service, module, old_mt5 = service_with_fake_mt5(journal, fake_mt5)
            try:
                result = service.run()
            finally:
                module.mt5 = old_mt5
            trade = journal.get_trade_by_ticket("8965515202")
            passed = result["closed_trades_updated"] == 0 and trade["status"] == "OPEN" and trade["profit_loss"] == -0.79 and fake_mt5.order_send_called is False and safety_ok(result)
            return show("Open trade remains OPEN if still in MT5 positions", passed, str(trade))
    except Exception as exc:
        return show("Open trade remains OPEN if still in MT5 positions", False, str(exc))


def verify_missing_history_warning_no_fake_close() -> bool:
    try:
        from backend.trade_journal.persistent_trade_journal_service import PersistentTradeJournalService

        with TemporaryDirectory() as tmp:
            journal = PersistentTradeJournalService(Path(tmp) / "trade_journal.json")
            journal.record_open_position(open_trade_payload())
            fake_mt5 = FakeMT5([], [])
            service, module, old_mt5 = service_with_fake_mt5(journal, fake_mt5)
            try:
                result = service.run()
            finally:
                module.mt5 = old_mt5
            trade = journal.get_trade_by_ticket("8965515202")
            passed = (
                result["closed_trades_updated"] == 0
                and result["warnings"][0]["warning"] == "CLOSE_HISTORY_NOT_FOUND"
                and trade["status"] == "OPEN"
                and trade["profit_loss"] == -0.79
                and safety_ok(result)
            )
            return show("Missing close history leaves trade OPEN with warning", passed, str(result))
    except Exception as exc:
        return show("Missing close history leaves trade OPEN with warning", False, str(exc))


def verify_closed_trade_updates_journal_and_summary() -> bool:
    try:
        from backend.trade_journal.persistent_trade_journal_service import PersistentTradeJournalService

        with TemporaryDirectory() as tmp:
            journal = PersistentTradeJournalService(Path(tmp) / "trade_journal.json")
            journal.record_open_position(open_trade_payload())
            fake_mt5 = FakeMT5([], [close_deal(3.14)])
            service, module, old_mt5 = service_with_fake_mt5(journal, fake_mt5)
            try:
                result = service.run()
                analytics = service.get_analytics()
            finally:
                module.mt5 = old_mt5
            trade = journal.get_trade_by_ticket("8965515202")
            summary = journal.calculate_realized_summary()
            passed = (
                result["closed_trades_updated"] == 1
                and trade["status"] == "CLOSED"
                and trade["result"] == "WIN"
                and trade["close_price"] == 1.15573
                and trade["realized_pnl"] == 3.14
                and trade["commission"] == -0.04
                and trade["swap"] == -0.1
                and trade["net_pnl"] == 3.0
                and trade["profit_loss"] == 3.0
                and trade["exit_reason"] == "TAKE_PROFIT"
                and trade["duration_minutes"] is not None
                and summary["closed_demo_trades"] == 1
                and summary["wins"] == 1
                and summary["win_rate"] == 100.0
                and summary["net_pnl"] == 3.0
                and summary["gross_profit"] == 3.0
                and analytics["realized_pnl"] == 3.0
                and fake_mt5.order_send_called is False
                and safety_ok(result)
                and safety_ok(analytics)
            )
            return show("Closed trade updates journal and realized summary", passed, str({"trade": trade, "summary": summary, "analytics": analytics}))
    except Exception as exc:
        return show("Closed trade updates journal and realized summary", False, str(exc))


def verify_result_classification_and_reporting() -> bool:
    try:
        from backend.client_analytics.reporting_engine_service import ReportingEngineService
        from backend.client_analytics.strategy_analytics_service import StrategyAnalyticsService
        from backend.trade_journal.persistent_trade_journal_service import PersistentTradeJournalService

        with TemporaryDirectory() as tmp:
            journal = PersistentTradeJournalService(Path(tmp) / "trade_journal.json")
            cases = [("1", 2.0, "WIN"), ("2", -2.0, "LOSS"), ("3", 0.14, "BREAKEVEN")]
            for suffix, profit, _result in cases:
                ticket = f"896551520{suffix}"
                journal.record_open_position(open_trade_payload(ticket))
                fake_mt5 = FakeMT5([], [close_deal(profit, ticket=int(ticket))])
                service, module, old_mt5 = service_with_fake_mt5(journal, fake_mt5)
                try:
                    service.run()
                finally:
                    module.mt5 = old_mt5
            trades = {trade["mt5_ticket"]: trade for trade in journal.get_closed_trades()}
            strategy = StrategyAnalyticsService(persistent_journal=journal).get_strategy_dashboard_performance()
            report = ReportingEngineService(journal).build_daily_report()
            passed = (
                trades["8965515201"]["result"] == "WIN"
                and trades["8965515202"]["result"] == "LOSS"
                and trades["8965515203"]["result"] == "BREAKEVEN"
                and strategy["closed_demo_trades"] == 3
                and strategy["net_pnl"] == -0.28
                and strategy["realized_pnl"] == 0.14
                and strategy["best_trade"] is not None
                and strategy["worst_trade"] is not None
                and report["summary"]["closed_demo_trades"] == 3
                and report["summary"]["net_pnl"] == -0.28
                and report["summary"]["realized_pnl"] == 0.14
                and report["summary"]["best_trade"] is not None
                and report["summary"]["worst_trade"] is not None
                and safety_ok(strategy)
                and safety_ok(report)
            )
            return show("WIN/LOSS/BREAKEVEN classification and analytics/reporting work", passed, str({"strategy": strategy, "report": report["summary"]}))
    except Exception as exc:
        return show("WIN/LOSS/BREAKEVEN classification and analytics/reporting work", False, str(exc))


def verify_dashboard_closed_state_exists() -> bool:
    text = DASHBOARD_PATH.read_text(encoding="utf-8")
    required = ["Realized P&L", "Exit Reason", "Close Time", "DEMO CLOSED", "/trade-journal/persistence/recent?limit=5"]
    missing = [token for token in required if token not in text]
    return show("Dashboard can display closed demo trade state", not missing, ", ".join(missing))


def verify_no_order_or_close_paths() -> bool:
    close_text = CLOSE_SYNC_PATH.read_text(encoding="utf-8")
    token = "mt5." + "order_send"
    forbidden = ["mt5.order_send", "order_send(", "order_close", "position_close", "close_order("]
    allowed = [
        "backend/demo_execution/mt5_demo_executor.py",
        "backend/mt5_demo/guarded_demo_order_sender_service.py",
    ]
    matches = [
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in (PROJECT_ROOT / "backend").rglob("*.py")
        if token in path.read_text(encoding="utf-8", errors="ignore")
    ]
    present = [item for item in forbidden if item in close_text]
    return show("No order_send or close order path added", not present and sorted(matches) == allowed, ", ".join(present + matches))


def main() -> int:
    print("Phase 18 Day 4 Trade Close Sync Verification")
    print("=" * 78)
    checks = [
        verify_routes_exist(),
        verify_still_open_remains_open(),
        verify_missing_history_warning_no_fake_close(),
        verify_closed_trade_updates_journal_and_summary(),
        verify_result_classification_and_reporting(),
        verify_dashboard_closed_state_exists(),
        verify_no_order_or_close_paths(),
    ]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
