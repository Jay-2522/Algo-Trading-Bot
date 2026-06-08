import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

MONITOR_PATH = PROJECT_ROOT / "backend/mt5_demo/mt5_position_monitoring_service.py"
ANALYTICS_PATH = PROJECT_ROOT / "backend/client_analytics/demo_position_analytics_service.py"
DASHBOARD_PATH = PROJECT_ROOT / "frontend/components/dashboard/DashboardShell.tsx"

POSITION_MONITOR_ROUTES = {
    "/mt5-demo/position-monitor/status",
    "/mt5-demo/position-monitor/open",
    "/mt5-demo/position-monitor/open/{symbol}",
    "/mt5-demo/position-monitor/ticket/{ticket}",
    "/mt5-demo/position-monitor/sync",
}

ANALYTICS_ROUTES = {
    "/client-analytics/demo-positions/status",
    "/client-analytics/demo-positions/open",
    "/client-analytics/demo-positions/summary",
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
        raise AssertionError("order_send must not be called by monitoring")


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
        price_open=1.15259,
        sl=1.14973,
        tp=1.15573,
        price_current=1.1518,
        profit=-0.79,
        time=1780914095,
        magic=17001,
        comment="PHASE17_SINGLE_D",
    )


def verify_routes_exist() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        paths = {route.path for route in app.routes if hasattr(route, "methods")}
        missing = sorted((POSITION_MONITOR_ROUTES | ANALYTICS_ROUTES) - paths)
        status = client.get("/mt5-demo/position-monitor/status")
        analytics = client.get("/client-analytics/demo-positions/status")
        passed = not missing and status.status_code == 200 and analytics.status_code == 200 and safety_ok(status.json()) and safety_ok(analytics.json())
        return show("Position monitor and analytics routes exist", passed, ", ".join(missing))
    except Exception as exc:
        return show("Position monitor and analytics routes exist", False, str(exc))


def verify_monitor_matching_and_no_fake_pnl() -> bool:
    try:
        from backend.mt5_demo import mt5_demo_position_sync_service as sync_module
        from backend.mt5_demo.mt5_demo_position_sync_service import MT5DemoPositionSyncService
        from backend.mt5_demo.mt5_position_monitoring_service import MT5PositionMonitoringService
        from backend.trade_journal.persistent_trade_journal_service import PersistentTradeJournalService

        with TemporaryDirectory() as tmp:
            journal = PersistentTradeJournalService(Path(tmp) / "trade_journal.json")
            old_mt5 = sync_module.mt5
            fake_mt5 = FakeMT5([sample_position()])
            sync_module.mt5 = fake_mt5
            try:
                sync_service = MT5DemoPositionSyncService(journal)
                sync_service.sync_journal()
                monitor = MT5PositionMonitoringService(sync_service, journal)
                result = monitor.get_open_positions()
                ticket_result = monitor.get_position_by_ticket("8965515202")
            finally:
                sync_module.mt5 = old_mt5
            position = result["positions"][0] if result["positions"] else {}
            passed = (
                result["status"] == "POSITIONS_FOUND"
                and result["positions_count"] == 1
                and position["ticket"] == 8965515202
                and position["symbol"] == "EURUSD"
                and position["journal_status"] == "OPEN"
                and position["lifecycle_status"] == "OPEN"
                and position["floating_pnl"] == -0.79
                and position["floating_pnl_percent"] is None
                and position["distance_to_sl"] is not None
                and position["distance_to_tp"] is not None
                and position["account_login"] == "123456"
                and position["server"] == "MetaQuotes-Demo"
                and ticket_result["status"] == "FOUND"
                and fake_mt5.order_send_called is False
                and safety_ok(result)
                and safety_ok(ticket_result)
            )
            return show("Journal matching works and P&L is real MT5 floating P&L", passed, str(position))
    except Exception as exc:
        return show("Journal matching works and P&L is real MT5 floating P&L", False, str(exc))


def verify_empty_state_no_fake_position() -> bool:
    try:
        from backend.mt5_demo import mt5_demo_position_sync_service as sync_module
        from backend.mt5_demo.mt5_demo_position_sync_service import MT5DemoPositionSyncService
        from backend.mt5_demo.mt5_position_monitoring_service import MT5PositionMonitoringService
        from backend.trade_journal.persistent_trade_journal_service import PersistentTradeJournalService

        with TemporaryDirectory() as tmp:
            journal = PersistentTradeJournalService(Path(tmp) / "trade_journal.json")
            old_mt5 = sync_module.mt5
            fake_mt5 = FakeMT5([])
            sync_module.mt5 = fake_mt5
            try:
                monitor = MT5PositionMonitoringService(MT5DemoPositionSyncService(journal), journal)
                result = monitor.sync()
            finally:
                sync_module.mt5 = old_mt5
            passed = result["status"] == "NO_OPEN_POSITIONS" and result["positions_count"] == 0 and result["positions"] == [] and safety_ok(result)
            return show("Open position route returns honest empty state", passed, str(result))
    except Exception as exc:
        return show("Open position route returns honest empty state", False, str(exc))


def verify_demo_position_analytics_summary() -> bool:
    try:
        from backend.client_analytics.demo_position_analytics_service import DemoPositionAnalyticsService
        from backend.mt5_demo import mt5_demo_position_sync_service as sync_module
        from backend.mt5_demo.mt5_demo_position_sync_service import MT5DemoPositionSyncService
        from backend.mt5_demo.mt5_position_monitoring_service import MT5PositionMonitoringService
        from backend.mt5_demo.mt5_trade_lifecycle_service import MT5TradeLifecycleService
        from backend.trade_journal.persistent_trade_journal_service import PersistentTradeJournalService

        with TemporaryDirectory() as tmp:
            journal = PersistentTradeJournalService(Path(tmp) / "trade_journal.json")
            old_mt5 = sync_module.mt5
            fake_mt5 = FakeMT5([sample_position()])
            sync_module.mt5 = fake_mt5
            try:
                sync_service = MT5DemoPositionSyncService(journal)
                sync_service.sync_journal()
                analytics = DemoPositionAnalyticsService(MT5PositionMonitoringService(sync_service, journal), MT5TradeLifecycleService(journal))
                summary = analytics.get_summary()
            finally:
                sync_module.mt5 = old_mt5
            passed = (
                summary["open_positions"] == 1
                and summary["total_floating_pnl"] == -0.79
                and summary["symbols"] == ["EURUSD"]
                and summary["largest_floating_profit"] == -0.79
                and summary["largest_floating_loss"] == -0.79
                and summary["lifecycle_open_count"] == 1
                and summary["lifecycle_closed_count"] == 0
                and fake_mt5.order_send_called is False
                and safety_ok(summary)
            )
            return show("Demo position analytics summary works", passed, str(summary))
    except Exception as exc:
        return show("Demo position analytics summary works", False, str(exc))


def verify_frontend_dashboard_sync_exists() -> bool:
    text = DASHBOARD_PATH.read_text(encoding="utf-8")
    required = [
        "/mt5-demo/position-monitor/open",
        "Open Demo MT5 Position",
        "No open MT5 demo positions.",
        "Floating P&L",
        "Lifecycle Status",
        "Journal Status",
    ]
    missing = [token for token in required if token not in text]
    return show("Dashboard can display open demo position", not missing, ", ".join(missing))


def verify_no_order_send_paths() -> bool:
    monitor_text = MONITOR_PATH.read_text(encoding="utf-8")
    analytics_text = ANALYTICS_PATH.read_text(encoding="utf-8")
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
    passed = "mt5.order_send" not in monitor_text and "order_send(" not in monitor_text and "mt5.order_send" not in analytics_text and "order_send(" not in analytics_text and sorted(matches) == allowed
    return show("No new order_send path exists", passed, ", ".join(matches))


def main() -> int:
    print("Phase 18 Day 3 Position Monitoring Dashboard Verification")
    print("=" * 78)
    checks = [
        verify_routes_exist(),
        verify_monitor_matching_and_no_fake_pnl(),
        verify_empty_state_no_fake_position(),
        verify_demo_position_analytics_summary(),
        verify_frontend_dashboard_sync_exists(),
        verify_no_order_send_paths(),
    ]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
