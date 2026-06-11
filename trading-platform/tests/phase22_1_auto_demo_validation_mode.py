import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

SERVICE_PATH = PROJECT_ROOT / "backend/auto_validation/auto_validation_service.py"
ROUTES_PATH = PROJECT_ROOT / "backend/api/auto_validation_routes.py"
DASHBOARD_PATH = PROJECT_ROOT / "frontend/components/dashboard/DashboardShell.tsx"
API_PATH = PROJECT_ROOT / "frontend/lib/clientOperatingDashboardApi.ts"
AUTO_VALIDATION_STATE_PATH = PROJECT_ROOT / "data/auto_validation/session_state.json"


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def signal(**overrides: Any) -> dict[str, Any]:
    payload = {
        "symbol": "XAUUSD",
        "signal": "BUY",
        "execution_status": "READY_FOR_PREVIEW",
        "risk_status": "APPROVED",
        "entry": 2350.0,
        "stop_loss": 2345.0,
        "take_profit": 2360.0,
        "risk_reward": 2.0,
        "confidence": 80,
        "signal_hash": "phase22-1-signal",
        "setup_reason": "Qualified validation setup.",
        "market_structure_state": {"trend_bias": "BUY"},
        "strategy_profile": "DEMO_COLLECTION",
        "strategy_components": {"bos": True, "choch": True, "fvg": True, "liquidity_sweep": True, "order_block": True, "session_valid": True},
        "candle_source": {"broker_source": "VANTAGE_DEMO", "source": "VANTAGE_DEMO", "account_login": "123", "server": "VantageMarkets-Demo", "account_type": "DEMO"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "live_execution_enabled": False,
        "broker_execution_enabled": False,
    }
    payload.update(overrides)
    return payload


class FakeSignals:
    def __init__(self, current: dict[str, Any]) -> None:
        self.current_signal = current

    def current(self, record_history: bool = False) -> dict[str, Any]:
        return {"signals": [self.current_signal]}

    def signal_for_symbol(self, symbol: str, record_history: bool = False, strategy_profile: str = "PRODUCTION") -> dict[str, Any]:
        return {**self.current_signal, "symbol": symbol, "strategy_profile": strategy_profile}


class FakeMarket:
    def __init__(self, tick: dict[str, Any] | None = None) -> None:
        self.tick = tick or {"status": "OK", "bid": 1.1, "ask": 1.2, "spread": 0.25}

    def get_symbol_tick(self, symbol: str) -> dict[str, Any]:
        return self.tick


class FakeGuarded:
    def __init__(self) -> None:
        self.market_data_service = FakeMarket()
        self.calls: list[dict[str, Any]] = []
        self.reject = False

    def send_test_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(payload)
        if self.reject:
            return {
                "status": "BLOCKED",
                "mt5_order_sent": False,
                "guarded_sender_used": True,
                "rejection_code": "TEST_REJECTION",
                "rejection_reason": "Sender rejected for test.",
                "failed_guard": "TEST_REJECTION",
            }
        return {"status": "DEMO_ORDER_SENT", "mt5_order_sent": True, "guarded_sender_used": True}


class FakeJournal:
    def __init__(self, trades: list[dict[str, Any]] | None = None) -> None:
        self._trades = trades or []

    def list_trades(self, limit: int = 100000) -> list[dict[str, Any]]:
        return self._trades[-limit:]


class FakePositions:
    def __init__(self, positions: list[dict[str, Any]] | None = None) -> None:
        self.positions = positions or []

    def get_open_positions(self) -> dict[str, Any]:
        return {"positions": self.positions, "positions_count": len(self.positions), "status": "POSITIONS_FOUND" if self.positions else "NO_OPEN_POSITIONS"}


class FakeAccount:
    def __init__(self, account_type: str = "DEMO", server: str = "VantageMarkets-Demo") -> None:
        self.account_type = account_type
        self.server = server

    def get_status(self) -> dict[str, Any]:
        return {"account_type": self.account_type, "server": self.server, "login": "123", "terminal_running": True, "status": "CONNECTED"}


def make_service(current: dict[str, Any] | None = None, *, positions=None, trades=None, account_type="DEMO", server="VantageMarkets-Demo"):
    from backend.auto_validation.auto_validation_service import AutoValidationService

    guarded = FakeGuarded()
    svc = AutoValidationService(
        signal_provider=FakeSignals(current or signal()),
        guarded_execution_service=guarded,
        journal_service=FakeJournal(trades),
        position_service=FakePositions(positions),
        mt5_demo_service=FakeAccount(account_type=account_type, server=server),
        state_path=Path(tempfile.mkdtemp()) / "state.json",
    )
    return svc, guarded


def verify_default_routes_and_config() -> bool:
    if AUTO_VALIDATION_STATE_PATH.exists():
        AUTO_VALIDATION_STATE_PATH.unlink()
    from backend.main import app
    from backend.api.auto_validation_routes import auto_validation_service

    auto_validation_service.config = auto_validation_service._default_config()
    auto_validation_service.session = auto_validation_service._empty_session()
    auto_validation_service.events = []
    auto_validation_service._last_execution_decision = None
    auto_validation_service._current_signal_watched = None
    client = TestClient(app)
    payload = client.get("/auto-validation/status").json()
    route_text = "\n".join(route.path for route in app.routes)
    required = [
        "/auto-validation/status",
        "/auto-validation/start",
        "/auto-validation/pause",
        "/auto-validation/resume",
        "/auto-validation/stop",
        "/auto-validation/trades",
        "/auto-validation/summary",
        "/auto-validation/events",
    ]
    passed = payload["config"]["auto_validation_enabled"] is False and payload["config"]["target_closed_trades"] == 30 and all(route in route_text for route in required)
    return show("Default disabled config and auto-validation routes exist", passed, str(payload["config"]))


def verify_lifecycle_controls() -> bool:
    svc, _ = make_service()
    started = svc.start()
    paused = svc.pause()
    resumed = svc.resume()
    stopped = svc.stop()
    passed = started["session"]["status"] == "RUNNING" and paused["session"]["status"] == "PAUSED" and resumed["session"]["status"] == "RUNNING" and stopped["session"]["status"] == "STOPPED"
    return show("Start, pause, resume, stop work", passed)


def verify_guarded_execution_and_blocks() -> bool:
    svc, guarded = make_service(signal_hash := signal())
    svc.start({"cooldown_after_trade_minutes": 15})
    sent = svc.run_once([signal_hash])
    duplicate = svc.run_once([signal_hash])
    passed = (
        sent["status"] == "ORDER_SENT"
        and len(guarded.calls) == 1
        and guarded.calls[0]["validation_session_id"] == svc.session["session_id"]
        and guarded.calls[0]["execution_mode"] == "AUTO_VALIDATION"
        and duplicate["status"] in {"BLOCKED", "HALTED_RISK"}
        and ("DUPLICATE_SIGNAL_BLOCKED" in duplicate["blockers"] or "COOLDOWN_ACTIVE" in duplicate["blockers"])
    )
    return show("Qualified AUTO validation signal uses guarded sender and duplicate/cooldown blocks", passed)


def verify_risk_blocks() -> bool:
    checks = []

    live, _ = make_service(account_type="LIVE")
    live.start()
    checks.append("LIVE_ACCOUNT_DETECTED" in live.run_once([signal(signal_hash="live")])["blockers"])

    broker, _ = make_service(server="OtherBroker-Demo")
    broker.start()
    checks.append("NON_VANTAGE_BROKER_DETECTED" in broker.run_once([signal(signal_hash="broker")])["blockers"])

    symbol_service, _ = make_service(signal(symbol="GBPUSD", signal_hash="bad-symbol"))
    symbol_service.start()
    symbol_result = symbol_service.run_once([signal(symbol="GBPUSD", signal_hash="bad-symbol")])
    checks.append(symbol_result["status"] == "NO_QUALIFIED_SIGNAL" and symbol_service.status()["current_signal_watched"] is None)

    lot_service, _ = make_service()
    lot_service.start({"lot_size": 0.02})
    checks.append(lot_service.config["lot_size"] == 0.01)

    sl_service, _ = make_service(signal(stop_loss=None, signal_hash="missing-sl"))
    sl_service.start()
    checks.append("SL_TP_REQUIRED" in sl_service.run_once([signal(stop_loss=None, signal_hash="missing-sl")])["blockers"])

    open_service, _ = make_service(positions=[{"symbol": "XAUUSD"}])
    open_service.start()
    checks.append("MAX_OPEN_TRADES_TOTAL_REACHED" in open_service.run_once([signal(signal_hash="open")])["blockers"])

    daily_service, _ = make_service()
    daily_service.start({"max_daily_trades": 0})
    checks.append("MAX_DAILY_TRADE_LIMIT_REACHED" in daily_service.run_once([signal(signal_hash="daily")])["blockers"])

    return show("Live, broker, symbol, lot, SL/TP, open trade, and daily limit guards work", all(checks))


def verify_target_and_risk_halt() -> bool:
    closed = [{"validation_session_id": "placeholder", "status": "CLOSED", "result": "WIN", "net_pnl": 1.0} for _ in range(30)]
    svc, _ = make_service(trades=closed)
    svc.start()
    for trade in closed:
      trade["validation_session_id"] = svc.session["session_id"]
    summary = svc.summary()

    loss_trades = [{"validation_session_id": "placeholder", "status": "CLOSED", "result": "LOSS", "net_pnl": -200.0}]
    risk, _ = make_service(trades=loss_trades)
    risk.start({"max_daily_loss_amount": 50})
    loss_trades[0]["validation_session_id"] = risk.session["session_id"]
    halted = risk.run_once([signal(signal_hash="risk")])
    passed = summary["status"] == "COMPLETED" and summary["current_closed_trades"] == 30 and halted["status"] == "HALTED_RISK"
    return show("Target 30 closed trades completes session and risk halt stops session", passed)


def verify_rejected_sender_does_not_halt() -> bool:
    svc, guarded = make_service(signal(signal_hash="reject"))
    guarded.reject = True
    svc.start()
    result = svc.run_once([signal(signal_hash="reject")])
    passed = (
        result["status"] == "BLOCKED"
        and "GUARDED_SENDER_REJECTED" in result["blockers"]
        and svc.session["status"] == "RUNNING"
        and svc.session["signals_blocked_by_sender"] == 1
        and svc.status()["last_sender_rejection"]["failed_guard"] == "TEST_REJECTION"
    )
    return show("Guarded sender rejection is logged without halting validation", passed, str(result))


def verify_validation_performance_metrics() -> bool:
    trades = [
        {
            "validation_session_id": "placeholder",
            "trade_id": "win-1",
            "status": "CLOSED",
            "result": "WIN",
            "net_pnl": 120.0,
            "risk_reward_ratio": 2.0,
            "closed_at": "2026-01-01T00:00:00+00:00",
            "strategy_metadata": {"strategy_components": {"bos": True, "fvg": True}},
        },
        {
            "validation_session_id": "placeholder",
            "trade_id": "loss-1",
            "status": "CLOSED",
            "result": "LOSS",
            "net_pnl": -40.0,
            "risk_reward_ratio": 1.5,
            "closed_at": "2026-01-01T00:01:00+00:00",
            "strategy_metadata": {"strategy_components": {"choch": True}},
        },
        {
            "validation_session_id": "placeholder",
            "trade_id": "win-2",
            "status": "CLOSED",
            "result": "WIN",
            "net_pnl": 60.0,
            "risk_reward_ratio": 3.0,
            "closed_at": "2026-01-01T00:02:00+00:00",
            "strategy_metadata": {"strategy_components": {"bos": True, "fvg": True}},
        },
        {"validation_session_id": "placeholder", "trade_id": "open-1", "status": "OPEN", "net_pnl": 0.0},
    ]
    svc, _ = make_service(trades=trades)
    svc.start()
    for trade in trades:
        trade["validation_session_id"] = svc.session["session_id"]
    summary = svc.summary()
    equity = summary["equity_curve"]
    passed = (
        summary["total_trades"] == 4
        and summary["current_closed_trades"] == 3
        and summary["current_open_trades"] == 1
        and summary["wins"] == 2
        and summary["losses"] == 1
        and summary["win_rate"] == 66.67
        and summary["net_pnl"] == 140.0
        and summary["avg_rr"] == 2.17
        and summary["profit_factor"] == 4.5
        and summary["max_drawdown"] == 40.0
        and summary["best_setup_type"] == "BOS + FVG"
        and summary["worst_setup_type"] == "CHOCH"
        and [point["equity"] for point in equity] == [120.0, 80.0, 140.0]
    )
    return show("Validation performance metrics and equity curve are generated", passed, str(summary))


def verify_dashboard_and_no_order_send() -> bool:
    service = SERVICE_PATH.read_text(encoding="utf-8")
    routes = ROUTES_PATH.read_text(encoding="utf-8")
    dashboard = DASHBOARD_PATH.read_text(encoding="utf-8")
    api = API_PATH.read_text(encoding="utf-8")
    required = [
        "AutoValidationService",
        "/auto-validation/status",
        "/auto-validation/start",
        "AutoValidationPanel",
        "Start 30-Trade Validation",
        "Emergency Stop",
        "validation_session_id",
        "AUTO_VALIDATION",
        "Validation Performance Dashboard",
        "Total Trades",
        "Average RR",
        "Profit Factor",
        "Best Setup Type",
        "Worst Setup Type",
        "Equity Curve",
    ]
    missing = [item for item in required if item not in service + routes + dashboard + api]
    token = "mt5." + "order_send"
    matches = [
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in (PROJECT_ROOT / "backend").rglob("*.py")
        if token in path.read_text(encoding="utf-8", errors="ignore")
    ]
    allowed = ["backend/demo_execution/mt5_demo_executor.py", "backend/mt5_demo/guarded_demo_order_sender_service.py"]
    return show("Dashboard data generated, guarded sender only, no unrestricted order_send", not missing and sorted(matches) == allowed, ", ".join(missing + matches))


def main() -> int:
    print("Phase 22.1 AUTO Demo Validation Mode Verification")
    print("=" * 78)
    checks = [
        verify_default_routes_and_config(),
        verify_lifecycle_controls(),
        verify_guarded_execution_and_blocks(),
        verify_risk_blocks(),
        verify_target_and_risk_halt(),
        verify_rejected_sender_does_not_halt(),
        verify_validation_performance_metrics(),
        verify_dashboard_and_no_order_send(),
    ]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
