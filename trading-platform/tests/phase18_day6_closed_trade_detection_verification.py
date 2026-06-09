import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

LIFECYCLE_PATH = PROJECT_ROOT / "backend/mt5_demo/mt5_trade_lifecycle_service.py"
CLOSE_SYNC_PATH = PROJECT_ROOT / "backend/mt5_demo/mt5_trade_close_sync_service.py"

OPEN_ORDER_TICKET = "8965515202"
OPEN_DEAL_TICKET = 8584944743
CLOSE_ORDER_TICKET = 9000000001
CLOSE_DEAL_TICKET = 9000000002


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


class FakeMT5:
    ACCOUNT_TRADE_MODE_DEMO = 0
    DEAL_ENTRY_IN = 0
    DEAL_ENTRY_OUT = 1
    DEAL_ENTRY_OUT_BY = 2

    def __init__(self) -> None:
        self.deal_ranges: list[tuple[Any, Any]] = []
        self.order_ranges: list[tuple[Any, Any]] = []

    def initialize(self) -> bool:
        return True

    def shutdown(self) -> None:
        return None

    def last_error(self) -> tuple[int, str]:
        return (0, "")

    def account_info(self) -> Any:
        return SimpleNamespace(login=123456, server="MetaQuotes-Demo", trade_mode=self.ACCOUNT_TRADE_MODE_DEMO)

    def positions_get(self) -> list[Any]:
        return []

    def history_deals_get(self, since: Any, now: Any) -> list[Any]:
        self.deal_ranges.append((since, now))
        return [
            SimpleNamespace(
                ticket=OPEN_DEAL_TICKET,
                order=int(OPEN_ORDER_TICKET),
                position_id=OPEN_DEAL_TICKET,
                symbol="EURUSD",
                volume=0.01,
                entry=self.DEAL_ENTRY_IN,
                profit=0.0,
                swap=0.0,
                commission=0.0,
                price=1.15273,
                time=1717833600,
            ),
            SimpleNamespace(
                ticket=CLOSE_DEAL_TICKET,
                order=CLOSE_ORDER_TICKET,
                position_id=OPEN_DEAL_TICKET,
                symbol="EURUSD",
                volume=0.01,
                entry=self.DEAL_ENTRY_OUT,
                profit=3.13,
                swap=0.0,
                commission=0.0,
                price=1.15573,
                time=1717837200,
            ),
        ]

    def history_orders_get(self, since: Any, now: Any) -> list[Any]:
        self.order_ranges.append((since, now))
        return [
            SimpleNamespace(ticket=int(OPEN_ORDER_TICKET), position_id=OPEN_DEAL_TICKET, position_by_id=0, symbol="EURUSD", volume_current=0.0, volume_initial=0.01),
            SimpleNamespace(ticket=CLOSE_ORDER_TICKET, position_id=OPEN_DEAL_TICKET, position_by_id=0, symbol="EURUSD", volume_current=0.0, volume_initial=0.01),
        ]


def seed_open_trade(journal) -> None:
    journal.record_open_position(
        {
            "trade_id": f"mt5_demo_{OPEN_ORDER_TICKET}",
            "source": "MT5_DEMO",
            "environment": "DEMO",
            "symbol": "EURUSD",
            "side": "BUY",
            "lot": 0.01,
            "entry_price": 1.15273,
            "stop_loss": 1.14973,
            "take_profit": 1.15573,
            "risk_reward_ratio": 2.0,
            "mt5_ticket": OPEN_ORDER_TICKET,
            "opened_at": "2024-06-08T08:00:00+00:00",
            "account_login": "123456",
            "server": "MetaQuotes-Demo",
            "notes": "First controlled MT5 demo order executed through guarded sender.",
        }
    )


def verify_lifecycle_detects_close_from_related_history_ids() -> bool:
    try:
        import backend.mt5_demo.mt5_trade_lifecycle_service as lifecycle_module
        from backend.mt5_demo.mt5_trade_lifecycle_service import MT5TradeLifecycleService
        from backend.trade_journal.persistent_trade_journal_service import PersistentTradeJournalService

        fake_mt5 = FakeMT5()
        original = lifecycle_module.mt5
        lifecycle_module.mt5 = fake_mt5
        try:
            with TemporaryDirectory() as tmp:
                journal = PersistentTradeJournalService(Path(tmp) / "trade_journal.json")
                seed_open_trade(journal)
                result = MT5TradeLifecycleService(journal).sync()
                summary = journal.get_summary()
                closed = journal.get_closed_trades()[0]
                passed = (
                    result["closed_trades_updated"] == 1
                    and result["history_deals_checked"] == 2
                    and result["history_orders_checked"] == 2
                    and summary["open_demo_trades"] == 0
                    and summary["closed_demo_trades"] == 1
                    and closed["mt5_ticket"] == OPEN_ORDER_TICKET
                    and closed["status"] == "CLOSED"
                    and closed["result"] == "WIN"
                    and closed["realized_pnl"] == 3.13
                    and closed["profit_loss"] == 3.13
                    and closed["duration_minutes"] is not None
                    and fake_mt5.deal_ranges
                    and safety_ok(result)
                    and safety_ok(summary)
                )
                return show("Lifecycle detects MT5 close through related order/deal IDs", passed, str({"result": result, "summary": summary, "closed": closed}))
        finally:
            lifecycle_module.mt5 = original
    except Exception as exc:
        return show("Lifecycle detects MT5 close through related order/deal IDs", False, str(exc))


def verify_close_sync_detects_close_from_related_history_ids() -> bool:
    try:
        import backend.mt5_demo.mt5_trade_close_sync_service as close_sync_module
        from backend.mt5_demo.mt5_trade_close_sync_service import MT5TradeCloseSyncService
        from backend.trade_journal.persistent_trade_journal_service import PersistentTradeJournalService

        fake_mt5 = FakeMT5()
        original = close_sync_module.mt5
        close_sync_module.mt5 = fake_mt5
        try:
            with TemporaryDirectory() as tmp:
                journal = PersistentTradeJournalService(Path(tmp) / "trade_journal.json")
                seed_open_trade(journal)
                result = MT5TradeCloseSyncService(journal).run()
                summary = journal.get_summary()
                closed = journal.get_closed_trades()[0]
                passed = (
                    result["closed_trades_updated"] == 1
                    and result["warnings"] == []
                    and result["history_deals_checked"] == 2
                    and result["history_orders_checked"] == 2
                    and summary["open_demo_trades"] == 0
                    and summary["closed_demo_trades"] == 1
                    and closed["result"] == "WIN"
                    and closed["net_pnl"] == 3.13
                    and closed["exit_reason"] == "TAKE_PROFIT"
                    and closed["duration_minutes"] is not None
                    and safety_ok(result)
                    and safety_ok(summary)
                )
                return show("Close sync detects MT5 close through related order/deal IDs", passed, str({"result": result, "summary": summary, "closed": closed}))
        finally:
            close_sync_module.mt5 = original
    except Exception as exc:
        return show("Close sync detects MT5 close through related order/deal IDs", False, str(exc))


def verify_history_lookup_and_safety() -> bool:
    lifecycle_text = LIFECYCLE_PATH.read_text(encoding="utf-8")
    close_sync_text = CLOSE_SYNC_PATH.read_text(encoding="utf-8")
    token = "mt5." + "order_send"
    matches = [
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in (PROJECT_ROOT / "backend").rglob("*.py")
        if token in path.read_text(encoding="utf-8", errors="ignore")
    ]
    allowed = [
        "backend/demo_execution/mt5_demo_executor.py",
        "backend/mt5_demo/guarded_demo_order_sender_service.py",
    ]
    required = [
        "history_deals_get",
        "history_orders_get",
        "_related_ticket_values",
        "_history_range",
        "history_deals_checked",
        "history_orders_checked",
    ]
    missing = [item for item in required if item not in lifecycle_text or item not in close_sync_text]
    forbidden = ["order_send(", "position_close", "close_order", "live_execution_enabled=True", "broker_execution_enabled=True"]
    present = [item for item in forbidden if item in lifecycle_text or item in close_sync_text]
    passed = not missing and not present and sorted(matches) == allowed
    return show("History lookup is read-only and no execution path was added", passed, ", ".join(missing + present + matches))


def main() -> int:
    print("Phase 18 Closed Trade Detection Verification")
    print("=" * 78)
    checks = [
        verify_lifecycle_detects_close_from_related_history_ids(),
        verify_close_sync_detects_close_from_related_history_ids(),
        verify_history_lookup_and_safety(),
    ]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
