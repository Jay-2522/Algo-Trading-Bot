import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

SERVICE_PATH = PROJECT_ROOT / "backend/auto_validation/exit_management_service.py"
AUTO_SERVICE_PATH = PROJECT_ROOT / "backend/auto_validation/auto_validation_service.py"
SENDER_PATH = PROJECT_ROOT / "backend/mt5_demo/guarded_demo_order_sender_service.py"
DASHBOARD_PATH = PROJECT_ROOT / "frontend/components/dashboard/DashboardShell.tsx"
API_PATH = PROJECT_ROOT / "frontend/lib/clientOperatingDashboardApi.ts"
ROUTES_PATH = PROJECT_ROOT / "backend/api/auto_validation_routes.py"


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


class FakeSignals:
    def __init__(self, signal: str = "BUY", confidence: float = 70) -> None:
        self.signal = signal
        self.confidence = confidence

    def signal_for_symbol(self, symbol: str, record_history: bool = False, strategy_profile: str = "DEMO_COLLECTION") -> dict[str, Any]:
        return {"symbol": symbol, "signal": self.signal, "confidence": self.confidence, "strategy_profile": strategy_profile}


class FakeMarket:
    def __init__(self, tick: dict[str, Any] | None = None) -> None:
        self.tick = tick or {"status": "OK", "bid": 111.0, "ask": 111.1, "spread": 0.2, "timestamp": datetime.now(timezone.utc).isoformat()}

    def get_symbol_tick(self, symbol: str) -> dict[str, Any]:
        return {**self.tick, "symbol": symbol}


class FakeSender:
    def __init__(self) -> None:
        self.sl_calls: list[dict[str, Any]] = []
        self.close_calls: list[dict[str, Any]] = []
        self.fail_close = False

    def modify_demo_position_stop(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.sl_calls.append(payload)
        return {"status": "SLTP_MODIFIED", "mt5_order_sent": True, "retcode": "10009"}

    def close_demo_position(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.close_calls.append(payload)
        if self.fail_close:
            return {"status": "EXIT_FAILED", "reason": "test failure", "retcode": "10030"}
        return {"status": "POSITION_CLOSED", "mt5_order_sent": True, "retcode": "10009"}


class FakeJournal:
    def __init__(self) -> None:
        self.updates: list[tuple[str, dict[str, Any]]] = []

    def record_exit_management_update(self, ticket: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.updates.append((ticket, payload))
        return payload


def config(**overrides: Any) -> dict[str, Any]:
    payload = {
        "strategy_profile": "DEMO_COLLECTION",
        "exit_management_enabled": True,
        "live_execution_enabled": False,
        "broker_execution_enabled": False,
        "break_even_trigger_r": 1.0,
        "trailing_stop_trigger_r": 1.5,
        "trailing_stop_distance_r": 0.75,
        "exit_stale_minutes": 45,
        "exit_stale_min_r": 0.2,
        "exit_soft_adverse_minutes": 20,
        "exit_no_progress_minutes": 30,
        "exit_no_progress_min_r": 0.3,
        "exit_confidence_floor": 40,
        "exit_confidence_drop_points": 25,
        "exit_max_close_retries": 3,
        "per_symbol_exit_settings": {
            "XAUUSD": {"max_spread": 1.0, "max_tick_age_seconds": 10, "break_even_trigger_r": 1.0, "trailing_stop_trigger_r": 1.5, "trailing_stop_distance_r": 0.75, "stale_exit_minutes": 45, "soft_adverse_minutes": 20, "no_progress_minutes": 30, "no_progress_min_r": 0.3, "confidence_floor": 40, "confidence_drop_points": 25},
            "EURUSD": {"max_spread": 0.0003, "max_tick_age_seconds": 10, "break_even_trigger_r": 1.0, "trailing_stop_trigger_r": 1.5, "trailing_stop_distance_r": 0.75, "stale_exit_minutes": 45, "soft_adverse_minutes": 20, "no_progress_minutes": 30, "no_progress_min_r": 0.3, "confidence_floor": 40, "confidence_drop_points": 25},
            "NIFTY50": {"max_spread": 5.0, "max_tick_age_seconds": 10},
        },
    }
    payload.update(overrides)
    return payload


def position(**overrides: Any) -> dict[str, Any]:
    payload = {
        "ticket": "7001",
        "symbol": "XAUUSD",
        "type": "BUY",
        "volume": 0.01,
        "price_open": 100.0,
        "price_current": 111.0,
        "sl": 95.0,
        "tp": 120.0,
        "profit": 5.0,
        "time": (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat(),
    }
    payload.update(overrides)
    return payload


def trade(**overrides: Any) -> dict[str, Any]:
    payload = {
        "trade_id": "mt5_demo_7001",
        "mt5_ticket": "7001",
        "validation_session_id": "phase24-session",
        "status": "OPEN",
        "symbol": "XAUUSD",
        "side": "BUY",
        "signal_confidence": 70,
    }
    payload.update(overrides)
    return payload


def service(signals: FakeSignals | None = None, market: FakeMarket | None = None, sender: FakeSender | None = None, journal: FakeJournal | None = None):
    from backend.auto_validation.exit_management_service import AutoValidationExitManagementService

    fake_sender = sender or FakeSender()
    fake_journal = journal or FakeJournal()
    return AutoValidationExitManagementService(signals or FakeSignals(), market or FakeMarket(), fake_sender, fake_journal), fake_sender, fake_journal


def run_with(pos: dict[str, Any], trd: dict[str, Any], *, signals: FakeSignals | None = None, market: FakeMarket | None = None, sender: FakeSender | None = None, cfg: dict[str, Any] | None = None):
    svc, fake_sender, fake_journal = service(signals, market, sender)
    result = svc.run(session={"status": "RUNNING", "session_id": "phase24-session"}, config=cfg or config(), positions=[pos], trades=[trd])
    return result, fake_sender, fake_journal


def verify_break_even_and_trailing() -> bool:
    be, be_sender, _ = run_with(position(price_current=105.0), trade())
    trailing, trailing_sender, _ = run_with(position(price_current=111.0), trade())
    be_decision = be["managed_positions"][0]
    trailing_decision = trailing["managed_positions"][0]
    passed = (
        be_decision["exit_reason"] == "BREAK_EVEN_PROTECTION"
        and be_decision["new_stop_loss"] == 100.0
        and len(be_sender.sl_calls) == 1
        and trailing_decision["exit_reason"] == "TRAILING_STOP"
        and trailing_decision["new_stop_loss"] > 100.0
        and len(trailing_sender.sl_calls) == 1
    )
    return show("Break-even and trailing stop updates use guarded demo SL modification", passed, str({"be": be_decision, "trailing": trailing_decision}))


def verify_close_reasons() -> bool:
    old = (datetime.now(timezone.utc) - timedelta(minutes=300)).isoformat()
    stale, stale_sender, _ = run_with(position(price_current=100.5, time=old), trade(), cfg=config(exit_stale_minutes=45))
    reversal, reversal_sender, _ = run_with(position(), trade(), signals=FakeSignals("SELL", 80))
    confidence, confidence_sender, _ = run_with(position(), trade(signal_confidence=70), signals=FakeSignals("BUY", 35))
    passed = (
        stale["managed_positions"][0]["exit_reason"] == "TIME_STALE_EXIT"
        and len(stale_sender.close_calls) == 1
        and reversal["managed_positions"][0]["exit_reason"] == "SIGNAL_REVERSAL_EXIT"
        and len(reversal_sender.close_calls) == 1
        and confidence["managed_positions"][0]["exit_reason"] == "CONFIDENCE_DROP_EXIT"
        and len(confidence_sender.close_calls) == 1
    )
    return show("Time-stale, signal reversal, and confidence-drop exits close through guarded demo sender", passed)


def verify_forward_validation_exit_rules() -> bool:
    old_negative = (datetime.now(timezone.utc) - timedelta(minutes=25)).isoformat()
    soft, soft_sender, _ = run_with(
        position(price_current=97.0, profit=-3.0, time=old_negative),
        trade(signal_confidence=70),
        signals=FakeSignals("WAIT", 35),
    )
    no_progress_time = (datetime.now(timezone.utc) - timedelta(minutes=35)).isoformat()
    no_progress, no_progress_sender, _ = run_with(
        position(price_current=101.0, profit=1.0, time=no_progress_time),
        trade(signal_confidence=70),
        signals=FakeSignals("BUY", 70),
    )
    hold, hold_sender, _ = run_with(
        position(price_current=102.0, profit=2.0, time=(datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()),
        trade(signal_confidence=70),
        signals=FakeSignals("BUY", 70),
    )
    hold_decision = hold["managed_positions"][0]
    passed = (
        soft["managed_positions"][0]["exit_reason"] == "SOFT_ADVERSE_EXIT"
        and len(soft_sender.close_calls) == 1
        and soft["soft_adverse_exits"] == 1
        and no_progress["managed_positions"][0]["exit_reason"] == "NO_PROGRESS_EXIT"
        and len(no_progress_sender.close_calls) == 1
        and no_progress["no_progress_exits"] == 1
        and hold_decision["action"] == "HOLD"
        and hold_decision["exit_reason"] == "HOLD_BELOW_BREAKEVEN_TRIGGER"
        and hold_decision["hold_checks"]["stale"] == "HOLD_WAITING_FOR_STALE_TIMEOUT"
        and hold_decision["hold_checks"]["reversal"] == "HOLD_NO_REVERSAL"
        and hold_decision["hold_checks"]["confidence"] == "HOLD_NO_CONFIDENCE_DROP"
        and len(hold_sender.close_calls) == 0
    )
    return show("Forward validation soft-adverse/no-progress exits and explicit HOLD reasons work", passed, str({"soft": soft["managed_positions"][0], "no_progress": no_progress["managed_positions"][0], "hold": hold_decision}))


def verify_safety_and_retry_guards() -> bool:
    stale_tick = {"status": "STALE_TICK", "bid": 111.0, "ask": 111.1, "spread": 0.2, "timestamp": (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()}
    unsafe, unsafe_sender, _ = run_with(position(), trade(), signals=FakeSignals("SELL", 80), market=FakeMarket(stale_tick))
    unowned, unowned_sender, _ = run_with(position(), trade(validation_session_id="old-session"), signals=FakeSignals("SELL", 80))
    failing_sender = FakeSender()
    failing_sender.fail_close = True
    failed, _, _ = run_with(position(), trade(), signals=FakeSignals("SELL", 80), sender=failing_sender)
    svc, duplicate_sender, _ = service(FakeSignals("SELL", 80), FakeMarket(), FakeSender())
    svc._active_close_tickets.add("7001")
    duplicate = svc.run(session={"status": "RUNNING", "session_id": "phase24-session"}, config=config(), positions=[position()], trades=[trade()])
    passed = (
        unsafe["blocked_actions"] == 1
        and "TICK_FRESHNESS_CHECK_FAILED" in unsafe["managed_positions"][0]["safety_blockers"]
        and len(unsafe_sender.close_calls) == 0
        and unowned["blocked_actions"] == 1
        and "POSITION_OWNERSHIP_NOT_CONFIRMED" in unowned["managed_positions"][0]["safety_blockers"]
        and len(unowned_sender.close_calls) == 0
        and failed["failed_actions"] == 1
        and failed["managed_positions"][0]["execution_result"]["status"] == "EXIT_FAILED"
        and duplicate["blocked_actions"] == 1
        and duplicate["managed_positions"][0]["execution_result"]["failed_guard"] == "DUPLICATE_CLOSE_ATTEMPT_IN_PROGRESS"
        and len(duplicate_sender.close_calls) == 0
    )
    return show("Exit safety blocks stale ticks/unowned positions, records close failures, and prevents duplicate close attempts", passed)


def verify_code_wiring_and_dashboard() -> bool:
    text = "\n".join(path.read_text(encoding="utf-8") for path in [SERVICE_PATH, AUTO_SERVICE_PATH, SENDER_PATH, DASHBOARD_PATH, API_PATH, ROUTES_PATH])
    required = [
        "AutoValidationExitManagementService",
        "run_exit_management",
        "/run-exit-management",
        "per_symbol_exit_settings",
        "NIFTY50",
        "VALID_TICK_REQUIRED",
        "POSITION_OWNERSHIP_NOT_CONFIRMED",
        "DUPLICATE_CLOSE_ATTEMPT_IN_PROGRESS",
        "EXIT_SL_MOVED",
        "EXIT_TRAILING_UPDATED",
        "EXIT_CLOSE_SUCCEEDED",
        "EXIT_CLOSE_FAILED",
        "Exit Management",
        "Open trade age",
        "Unrealized P&L",
        "SL Dist",
        "TP Dist",
        "exit_outcomes",
        "SOFT_ADVERSE_EXIT",
        "NO_PROGRESS_EXIT",
        "HOLD_BELOW_BREAKEVEN_TRIGGER",
        "HOLD_WAITING_FOR_STALE_TIMEOUT",
        "HOLD_NO_REVERSAL",
        "HOLD_NO_CONFIDENCE_DROP",
        "exit_soft_adverse_minutes",
        "exit_no_progress_minutes",
        "exit_no_progress_min_r",
        "live_execution_enabled",
    ]
    missing = [item for item in required if item not in text]
    token = "mt5." + "order_send"
    matches = [
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in (PROJECT_ROOT / "backend").rglob("*.py")
        if token in path.read_text(encoding="utf-8", errors="ignore")
    ]
    allowed = ["backend/demo_execution/mt5_demo_executor.py", "backend/mt5_demo/guarded_demo_order_sender_service.py"]
    return show("Phase 24 wiring, dashboard fields, per-symbol settings, and guarded order_send boundary exist", not missing and sorted(matches) == allowed, ", ".join(missing + matches))


def main() -> int:
    print("Phase 24 Exit Management Verification")
    print("=" * 78)
    checks = [
        verify_break_even_and_trailing(),
        verify_close_reasons(),
        verify_forward_validation_exit_rules(),
        verify_safety_and_retry_guards(),
        verify_code_wiring_and_dashboard(),
    ]
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
