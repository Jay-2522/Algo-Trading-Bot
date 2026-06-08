import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

LIFECYCLE_PATH = PROJECT_ROOT / "backend/mt5_demo/mt5_trade_lifecycle_service.py"

ROUTES = {
    "/mt5-demo/lifecycle/status",
    "/mt5-demo/lifecycle/sync",
    "/mt5-demo/lifecycle/latest",
    "/mt5-demo/lifecycle/history",
    "/mt5-demo/lifecycle/analytics",
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
        raise AssertionError("order_send must not be called by lifecycle sync")


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


def open_trade_payload() -> dict[str, Any]:
    return {
        "trade_id": "mt5_demo_8965515202",
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
        "mt5_ticket": "8965515202",
        "account_login": "123456",
        "server": "MetaQuotes-Demo",
        "opened_at": "2026-06-08T07:58:58+00:00",
        "notes": "Synced from MT5 open position.",
    }


def close_deal() -> Any:
    return SimpleNamespace(
        ticket=8584944743,
        order=8584944743,
        position_id=8965515202,
        symbol="EURUSD",
        volume=0.01,
        price=1.15573,
        profit=3.14,
        swap=-0.1,
        commission=-0.04,
        time=1780917695,
        entry=1,
        comment="closed by tp",
    )


def verify_routes_exist() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        paths = {route.path for route in app.routes if hasattr(route, "methods")}
        missing = sorted(ROUTES - paths)
        status = client.get("/mt5-demo/lifecycle/status")
        analytics = client.get("/mt5-demo/lifecycle/analytics")
        passed = not missing and status.status_code == 200 and analytics.status_code == 200 and safety_ok(status.json()) and safety_ok(analytics.json())
        return show("Lifecycle routes exist", passed, ", ".join(missing))
    except Exception as exc:
        return show("Lifecycle routes exist", False, str(exc))


def verify_open_to_closed_transition_and_analytics() -> bool:
    try:
        from backend.mt5_demo import mt5_trade_lifecycle_service as module
        from backend.mt5_demo.mt5_trade_lifecycle_service import MT5TradeLifecycleService
        from backend.trade_journal.persistent_trade_journal_service import PersistentTradeJournalService

        with TemporaryDirectory() as tmp:
            journal = PersistentTradeJournalService(Path(tmp) / "trade_journal.json")
            journal.record_open_position(open_trade_payload())
            old_mt5 = module.mt5
            fake_mt5 = FakeMT5(positions=[], deals=[close_deal()])
            module.mt5 = fake_mt5
            try:
                service = MT5TradeLifecycleService(journal)
                sync = service.sync()
                analytics = service.get_analytics()
            finally:
                module.mt5 = old_mt5
            trades = journal.get_recent_trades(limit=10)
            trade = trades[0] if trades else {}
            passed = (
                sync["status"] == "SYNCED"
                and sync["closed_trades_updated"] == 1
                and len(trades) == 1
                and trade["status"] == "CLOSED"
                and trade["result"] == "WIN"
                and trade["close_price"] == 1.15573
                and trade["realized_pnl"] == 3.14
                and trade["swap"] == -0.1
                and trade["commission"] == -0.04
                and trade["total_pnl"] == 3.0
                and trade["profit_loss"] == 3.0
                and trade["duration_minutes"] is not None
                and trade["exit_reason"] == "TAKE_PROFIT"
                and analytics["total_trades"] == 1
                and analytics["closed_trades"] == 1
                and analytics["wins"] == 1
                and analytics["losses"] == 0
                and analytics["win_rate"] == 100.0
                and analytics["net_pnl"] == 3.0
                and analytics["avg_pnl"] == 3.0
                and analytics["avg_duration"] > 0
                and analytics["avg_rr"] == 2.0
                and fake_mt5.order_send_called is False
                and safety_ok(sync)
                and safety_ok(analytics)
            )
            return show("Journal OPEN to CLOSED transition and analytics work", passed, str({"trade": trade, "analytics": analytics}))
    except Exception as exc:
        return show("Journal OPEN to CLOSED transition and analytics work", False, str(exc))


def verify_still_open_remains_open() -> bool:
    try:
        from backend.mt5_demo import mt5_trade_lifecycle_service as module
        from backend.mt5_demo.mt5_trade_lifecycle_service import MT5TradeLifecycleService
        from backend.trade_journal.persistent_trade_journal_service import PersistentTradeJournalService

        with TemporaryDirectory() as tmp:
            journal = PersistentTradeJournalService(Path(tmp) / "trade_journal.json")
            journal.record_open_position(open_trade_payload())
            open_position = SimpleNamespace(ticket=8965515202, symbol="EURUSD", volume=0.01)
            old_mt5 = module.mt5
            fake_mt5 = FakeMT5(positions=[open_position], deals=[close_deal()])
            module.mt5 = fake_mt5
            try:
                service = MT5TradeLifecycleService(journal)
                sync = service.sync()
            finally:
                module.mt5 = old_mt5
            trade = journal.get_recent_trades(limit=10)[0]
            passed = (
                sync["closed_trades_updated"] == 0
                and trade["status"] == "OPEN"
                and trade["profit_loss"] == -0.79
                and fake_mt5.order_send_called is False
                and safety_ok(sync)
            )
            return show("Still-open MT5 trade remains OPEN", passed, str(trade))
    except Exception as exc:
        return show("Still-open MT5 trade remains OPEN", False, str(exc))


def verify_no_matching_close_leaves_unchanged() -> bool:
    try:
        from backend.mt5_demo import mt5_trade_lifecycle_service as module
        from backend.mt5_demo.mt5_trade_lifecycle_service import MT5TradeLifecycleService
        from backend.trade_journal.persistent_trade_journal_service import PersistentTradeJournalService

        with TemporaryDirectory() as tmp:
            journal = PersistentTradeJournalService(Path(tmp) / "trade_journal.json")
            journal.record_open_position(open_trade_payload())
            old_mt5 = module.mt5
            fake_mt5 = FakeMT5(positions=[], deals=[])
            module.mt5 = fake_mt5
            try:
                service = MT5TradeLifecycleService(journal)
                sync = service.sync()
            finally:
                module.mt5 = old_mt5
            trade = journal.get_recent_trades(limit=10)[0]
            passed = (
                sync["closed_trades_updated"] == 0
                and sync["unchanged_trades"][0]["reason"] == "NO_MATCHING_MT5_CLOSE"
                and trade["status"] == "OPEN"
                and trade["profit_loss"] == -0.79
                and fake_mt5.order_send_called is False
                and safety_ok(sync)
            )
            return show("No matching MT5 close leaves journal unchanged", passed, str(trade))
    except Exception as exc:
        return show("No matching MT5 close leaves journal unchanged", False, str(exc))


def verify_no_order_send_paths() -> bool:
    lifecycle_text = LIFECYCLE_PATH.read_text(encoding="utf-8")
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
    passed = "mt5.order_send" not in lifecycle_text and "order_send(" not in lifecycle_text and sorted(matches) == allowed
    return show("No new order_send path exists", passed, ", ".join(matches))


def main() -> int:
    print("Phase 18 Day 2 Trade Lifecycle Verification")
    print("=" * 78)
    checks = [
        verify_routes_exist(),
        verify_open_to_closed_transition_and_analytics(),
        verify_still_open_remains_open(),
        verify_no_matching_close_leaves_unchanged(),
        verify_no_order_send_paths(),
    ]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
