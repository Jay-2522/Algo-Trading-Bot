import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

SENDER_PATH = PROJECT_ROOT / "backend/mt5_demo/guarded_demo_order_sender_service.py"


class StubService:
    def get_status(self) -> dict[str, Any]:
        return {}

    def get_latest(self) -> dict[str, Any]:
        return {}

    def get_latest_approval(self) -> dict[str, Any]:
        return {}

    def get_latest_audit(self) -> dict[str, Any]:
        return {}


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def sender_text() -> str:
    return SENDER_PATH.read_text(encoding="utf-8")


def build_guarded_sender(journal):
    from backend.mt5_demo.guarded_demo_order_sender_service import GuardedDemoOrderSenderService

    stub = StubService()
    return GuardedDemoOrderSenderService(
        mt5_demo_service=stub,
        approval_workflow_service=stub,
        final_approval_service=stub,
        dry_run_service=stub,
        preflight_service=stub,
        simulator_service=stub,
        readiness_service=stub,
        persistent_trade_journal_service=journal,
    )


def payload() -> dict[str, Any]:
    return {
        "environment": "DEMO",
        "symbol": "EURUSD",
        "action": "BUY",
        "lot": 0.01,
        "entry_price": 1.1,
        "stop_loss": 1.095,
        "take_profit": 1.11,
    }


def verify_successful_guarded_result_writes_journal() -> bool:
    try:
        from backend.trade_journal.persistent_trade_journal_service import PersistentTradeJournalService

        with TemporaryDirectory() as tmp:
            journal = PersistentTradeJournalService(Path(tmp) / "trade_journal.json")
            sender = build_guarded_sender(journal)
            result = {
                "request_id": "guarded-demo-order-test-success",
                "status": "DEMO_ORDER_SENT",
                "mt5_order_sent": True,
                "demo_order_attempted": True,
                "ticket": "8965515202",
                "retcode": "10009",
                "comment": "Request executed",
                "final_comment": "Request executed",
            }
            sender._persist_trade_journal_result(result, payload(), executed_price=1.1002)
            trades = journal.get_recent_trades()
            summary = journal.get_summary()
            trade = trades[0] if trades else {}
            passed = (
                len(trades) == 1
                and trade["source"] == "MT5_DEMO"
                and trade["environment"] == "DEMO"
                and trade["symbol"] == "EURUSD"
                and trade["side"] == "BUY"
                and trade["lot"] == 0.01
                and trade["entry_price"] == 1.1002
                and trade["stop_loss"] == 1.095
                and trade["take_profit"] == 1.11
                and trade["risk_reward_ratio"] == 2.0
                and trade["status"] == "SENT"
                and trade["result"] == "OPEN"
                and trade["mt5_ticket"] == "8965515202"
                and trade["mt5_retcode"] == "10009"
                and trade["mt5_comment"] == "Request executed"
                and trade["profit_loss"] == 0.0
                and "First controlled MT5 demo order executed through guarded sender." in trade["notes"]
                and summary["total_trades"] == 1
                and summary["sent_demo_orders"] == 1
                and summary["net_pnl"] == 0.0
            )
            return show("Successful guarded sender result writes persistent journal", passed, str(trade))
    except Exception as exc:
        return show("Successful guarded sender result writes persistent journal", False, str(exc))


def verify_rejected_attempt_can_write_rejection() -> bool:
    try:
        from backend.trade_journal.persistent_trade_journal_service import PersistentTradeJournalService

        with TemporaryDirectory() as tmp:
            journal = PersistentTradeJournalService(Path(tmp) / "trade_journal.json")
            sender = build_guarded_sender(journal)
            result = {
                "request_id": "guarded-demo-order-test-rejected",
                "status": "DEMO_ORDER_REJECTED",
                "mt5_order_sent": False,
                "demo_order_attempted": True,
                "ticket": "0",
                "retcode": "10030",
                "comment": "Unsupported filling mode",
                "final_comment": "Unsupported filling mode",
            }
            sender._persist_trade_journal_result(result, payload(), executed_price=None)
            trades = journal.get_recent_trades()
            summary = journal.get_summary()
            trade = trades[0] if trades else {}
            passed = (
                len(trades) == 1
                and trade["status"] == "REJECTED"
                and trade["result"] == "REJECTED"
                and trade["mt5_ticket"] == "0"
                and trade["mt5_retcode"] == "10030"
                and trade["mt5_comment"] == "Unsupported filling mode"
                and trade["profit_loss"] == 0.0
                and summary["total_trades"] == 1
                and summary["rejected_trades"] == 1
                and summary["sent_demo_orders"] == 0
                and summary["net_pnl"] == 0.0
            )
            return show("Rejected attempted sender result can write rejection", passed, str(trade))
    except Exception as exc:
        return show("Rejected attempted sender result can write rejection", False, str(exc))


def verify_source_contains_persistence_paths() -> bool:
    text = sender_text()
    required = [
        "PersistentTradeJournalService",
        "def _persist_trade_journal_result",
        'result.get("status") == "DEMO_ORDER_SENT"',
        'result.get("mt5_order_sent") is True',
        "retcode == 10009",
        "ticket > 0",
        "record_order_sent",
        'result.get("status") == "DEMO_ORDER_REJECTED"',
        'result.get("mt5_order_sent") is False',
        "record_order_rejected",
        '"source": "MT5_DEMO"',
        '"profit_loss": 0',
    ]
    missing = [token for token in required if token not in text]
    return show("Guarded sender source contains journal persistence paths", not missing, ", ".join(missing))


def verify_no_extra_order_send() -> bool:
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
    return show("No extra mt5.order_send path exists", sorted(matches) == allowed, ", ".join(matches))


def main() -> int:
    print("Phase 17 Day 3 Journal Persistence After Demo Order Verification")
    print("=" * 78)
    checks = [
        verify_source_contains_persistence_paths(),
        verify_successful_guarded_result_writes_journal(),
        verify_rejected_attempt_can_write_rejection(),
        verify_no_extra_order_send(),
    ]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
