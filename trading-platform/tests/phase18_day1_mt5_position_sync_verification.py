import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

SYNC_SERVICE_PATH = PROJECT_ROOT / "backend/mt5_demo/mt5_demo_position_sync_service.py"

ROUTES = {
    "/mt5-demo/positions/status",
    "/mt5-demo/positions/open",
    "/mt5-demo/positions/open/{symbol}",
    "/mt5-demo/positions/sync-journal",
    "/mt5-demo/positions/latest-sync",
}


class FakeMT5:
    ACCOUNT_TRADE_MODE_DEMO = 0
    POSITION_TYPE_BUY = 0
    POSITION_TYPE_SELL = 1

    def __init__(self, positions: list[Any]) -> None:
        self.positions = positions
        self.order_send_called = False

    def initialize(self) -> bool:
        return True

    def shutdown(self) -> None:
        return None

    def last_error(self) -> tuple[int, str]:
        return (0, "OK")

    def account_info(self) -> Any:
        return SimpleNamespace(login=123456, server="MetaQuotes-Demo", trade_mode=self.ACCOUNT_TRADE_MODE_DEMO)

    def positions_get(self, symbol: str | None = None) -> list[Any]:
        if symbol:
            return [position for position in self.positions if position.symbol == symbol]
        return self.positions

    def order_send(self, _request: dict[str, Any]) -> None:
        self.order_send_called = True
        raise AssertionError("order_send must not be called by position sync")


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


def sample_position() -> Any:
    return SimpleNamespace(
        ticket=8965515202,
        symbol="EURUSD",
        type=0,
        volume=0.01,
        price_open=1.15173,
        sl=1.14973,
        tp=1.15573,
        price_current=1.152,
        profit=0.27,
        time=1780900000,
        magic=17001,
        comment="PHASE17_SINGLE_DEMO_TEST",
    )


def verify_routes_exist() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        paths = {route.path for route in app.routes if hasattr(route, "methods")}
        missing = sorted(ROUTES - paths)
        status = client.get("/mt5-demo/positions/status")
        passed = not missing and status.status_code == 200 and safety_ok(status.json())
        return show("MT5 demo position routes exist", passed, ", ".join(missing))
    except Exception as exc:
        return show("MT5 demo position routes exist", False, str(exc))


def verify_normalization_handles_sample_position() -> bool:
    try:
        from backend.mt5_demo import mt5_demo_position_sync_service as module
        from backend.mt5_demo.mt5_demo_position_sync_service import MT5DemoPositionSyncService

        old_mt5 = module.mt5
        fake_mt5 = FakeMT5([sample_position()])
        module.mt5 = fake_mt5
        try:
            service = MT5DemoPositionSyncService()
            result = service.get_open_positions_by_symbol("EURUSD")
        finally:
            module.mt5 = old_mt5
        position = result["positions"][0] if result.get("positions") else {}
        passed = (
            result["status"] == "POSITIONS_FOUND"
            and result["positions_count"] == 1
            and position["ticket"] == 8965515202
            and position["symbol"] == "EURUSD"
            and position["type"] == "BUY"
            and position["volume"] == 0.01
            and position["price_open"] == 1.15173
            and position["sl"] == 1.14973
            and position["tp"] == 1.15573
            and position["price_current"] == 1.152
            and position["profit"] == 0.27
            and position["account_login"] == "123456"
            and position["server"] == "MetaQuotes-Demo"
            and safety_ok(result)
            and fake_mt5.order_send_called is False
        )
        return show("Normalization handles sample MT5 position objects", passed, str(position))
    except Exception as exc:
        return show("Normalization handles sample MT5 position objects", False, str(exc))


def verify_journal_upsert_by_mt5_ticket() -> bool:
    try:
        from backend.mt5_demo import mt5_demo_position_sync_service as module
        from backend.mt5_demo.mt5_demo_position_sync_service import MT5DemoPositionSyncService
        from backend.trade_journal.persistent_trade_journal_service import PersistentTradeJournalService

        with TemporaryDirectory() as tmp:
            journal = PersistentTradeJournalService(Path(tmp) / "trade_journal.json")
            old_mt5 = module.mt5
            first = sample_position()
            second = sample_position()
            second.profit = 0.42
            fake_mt5 = FakeMT5([first])
            module.mt5 = fake_mt5
            try:
                service = MT5DemoPositionSyncService(journal)
                first_sync = service.sync_journal()
                fake_mt5.positions = [second]
                second_sync = service.sync_journal()
            finally:
                module.mt5 = old_mt5
            trades = journal.get_recent_trades(limit=10)
            summary = journal.get_summary()
            trade = trades[0] if trades else {}
            passed = (
                first_sync["synced_count"] == 1
                and second_sync["synced_count"] == 1
                and len(trades) == 1
                and trade["trade_id"] == "mt5_demo_8965515202"
                and trade["status"] == "OPEN"
                and trade["result"] == "OPEN"
                and trade["source"] == "MT5_DEMO"
                and trade["environment"] == "DEMO"
                and trade["mt5_ticket"] == "8965515202"
                and trade["symbol"] == "EURUSD"
                and trade["side"] == "BUY"
                and trade["lot"] == 0.01
                and trade["entry_price"] == 1.15173
                and trade["stop_loss"] == 1.14973
                and trade["take_profit"] == 1.15573
                and trade["profit_loss"] == 0.42
                and "Synced from MT5 open position." in trade["notes"]
                and summary["total_trades"] == 1
                and summary["open_demo_trades"] == 1
                and summary["sent_demo_orders"] == 0
                and fake_mt5.order_send_called is False
                and safety_ok(first_sync)
                and safety_ok(second_sync)
            )
            return show("Journal upsert by mt5_ticket works", passed, str(trade))
    except Exception as exc:
        return show("Journal upsert by mt5_ticket works", False, str(exc))


def verify_no_fake_position_created() -> bool:
    try:
        from backend.mt5_demo import mt5_demo_position_sync_service as module
        from backend.mt5_demo.mt5_demo_position_sync_service import MT5DemoPositionSyncService
        from backend.trade_journal.persistent_trade_journal_service import PersistentTradeJournalService

        with TemporaryDirectory() as tmp:
            journal = PersistentTradeJournalService(Path(tmp) / "trade_journal.json")
            old_mt5 = module.mt5
            fake_mt5 = FakeMT5([])
            module.mt5 = fake_mt5
            try:
                service = MT5DemoPositionSyncService(journal)
                result = service.sync_journal()
            finally:
                module.mt5 = old_mt5
            summary = journal.get_summary()
            passed = (
                result["status"] == "NO_OPEN_POSITIONS"
                and result["synced_count"] == 0
                and result["journal_records"] == []
                and summary["total_trades"] == 0
                and summary["net_pnl"] == 0.0
                and fake_mt5.order_send_called is False
                and safety_ok(result)
            )
            return show("No fake position is created when MT5 returns none", passed, str(summary))
    except Exception as exc:
        return show("No fake position is created when MT5 returns none", False, str(exc))


def verify_sync_service_does_not_call_order_send() -> bool:
    text = SYNC_SERVICE_PATH.read_text(encoding="utf-8")
    return show("Sync service does not call order_send", "mt5.order_send" not in text and "order_send(" not in text)


def verify_no_new_unrestricted_order_send() -> bool:
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
    return show("No new unrestricted mt5.order_send exists", sorted(matches) == allowed, ", ".join(matches))


def main() -> int:
    print("Phase 18 Day 1 MT5 Position Sync Verification")
    print("=" * 78)
    checks = [
        verify_routes_exist(),
        verify_sync_service_does_not_call_order_send(),
        verify_normalization_handles_sample_position(),
        verify_journal_upsert_by_mt5_ticket(),
        verify_no_fake_position_created(),
        verify_no_new_unrestricted_order_send(),
    ]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
