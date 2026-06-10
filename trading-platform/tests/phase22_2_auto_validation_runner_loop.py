import asyncio
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

SERVICE_PATH = PROJECT_ROOT / "backend/auto_validation/auto_validation_service.py"
RUNNER_PATH = PROJECT_ROOT / "backend/auto_validation/auto_validation_runner.py"
ROUTES_PATH = PROJECT_ROOT / "backend/api/auto_validation_routes.py"
MAIN_PATH = PROJECT_ROOT / "backend/main.py"
DASHBOARD_PATH = PROJECT_ROOT / "frontend/components/dashboard/DashboardShell.tsx"


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def wait_signal(symbol: str = "XAUUSD", *, status_level: str = "WATCHLIST", signal_hash: str = "runner-wait") -> dict[str, Any]:
    return {
        "symbol": symbol,
        "signal": "WAIT",
        "status_level": status_level,
        "confidence": 70 if status_level == "WATCHLIST" else 30,
        "execution_status": "WAITING",
        "risk_status": "REJECTED",
        "signal_hash": signal_hash,
        "setup_reason": "Runner test signal is not executable.",
        "missing_requirements": [{"code": "BOS_MISSING", "label": "BOS confirmation is missing."}],
        "what_needs_to_happen_next": "Wait for a fully approved setup.",
        "entry": None,
        "stop_loss": None,
        "take_profit": None,
        "risk_reward": None,
        "candle_source": {"broker_source": "VANTAGE_DEMO", "server": "VantageMarkets-Demo", "account_type": "DEMO"},
    }


class FakeSignals:
    def __init__(self, signals: list[dict[str, Any]] | None = None, *, fail: bool = False) -> None:
        self.signals = signals or [wait_signal()]
        self.fail = fail

    def current(self, record_history: bool = False) -> dict[str, Any]:
        if self.fail:
            raise RuntimeError("signal provider failed")
        return {"signals": self.signals}

    def signal_for_symbol(self, symbol: str, record_history: bool = False) -> dict[str, Any]:
        return next((signal for signal in self.signals if signal.get("symbol") == symbol), wait_signal(symbol))


class FakeGuarded:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.market_data_service = self

    def get_symbol_tick(self, symbol: str) -> dict[str, Any]:
        return {"status": "OK", "spread": 0.2}

    def send_test_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(payload)
        return {"status": "DEMO_ORDER_SENT", "mt5_order_sent": True}


class FakeJournal:
    def list_trades(self, limit: int = 100000) -> list[dict[str, Any]]:
        return []


class FakePositions:
    def get_open_positions(self) -> dict[str, Any]:
        return {"positions": []}


class FakeAccount:
    def get_status(self) -> dict[str, Any]:
        return {"account_type": "DEMO", "server": "VantageMarkets-Demo"}


def make_service(signals: FakeSignals | None = None, state_path: Path | None = None):
    from backend.auto_validation.auto_validation_service import AutoValidationService

    guarded = FakeGuarded()
    return (
        AutoValidationService(
            signal_provider=signals or FakeSignals(),
            guarded_execution_service=guarded,
            journal_service=FakeJournal(),
            position_service=FakePositions(),
            mt5_demo_service=FakeAccount(),
            state_path=state_path,
        ),
        guarded,
    )


async def verify_runner_lifecycle() -> bool:
    from backend.auto_validation.auto_validation_runner import AutoValidationRunner

    with tempfile.TemporaryDirectory() as tmp:
        service, guarded = make_service(state_path=Path(tmp) / "state.json")
        runner = AutoValidationRunner(service, default_interval_seconds=0.05, watchlist_interval_seconds=0.03)
        service.start()
        runner.start()
        await asyncio.sleep(0.12)
        started = runner.is_active() and any(event["event"] == "SIGNAL_EVALUATED" for event in service.events)

        service.pause()
        runner.stop()
        await asyncio.sleep(0.01)
        paused = not runner.is_active()

        service.resume()
        runner.start()
        await asyncio.sleep(0.08)
        resumed = runner.is_active()

        service.stop()
        runner.stop()
        await asyncio.sleep(0.01)
        stopped = not runner.is_active()

        service.start()
        runner.start()
        await asyncio.sleep(0.05)
        service.emergency_stop()
        runner.stop()
        await asyncio.sleep(0.01)
        emergency_stopped = not runner.is_active() and service.session["status"] == "HALTED_RISK"

        await runner.shutdown()
        passed = started and paused and resumed and stopped and emergency_stopped and len(guarded.calls) == 0
        return show("Start, pause, resume, stop, and emergency stop control runner without orders", passed)


async def verify_run_once_called_and_events_generated() -> bool:
    from backend.auto_validation.auto_validation_runner import AutoValidationRunner

    with tempfile.TemporaryDirectory() as tmp:
        service, _ = make_service(state_path=Path(tmp) / "state.json")
        runner = AutoValidationRunner(service)
        service.start()
        result = await runner.run_tick()
        status = service.status()
        events = [event["event"] for event in service.events]
        passed = (
            result["status"] == "NO_QUALIFIED_SIGNAL"
            and "SIGNAL_EVALUATED" in events
            and "NO_QUALIFIED_SIGNAL" in events
            and status["current_signal_watched"] is not None
            and status["last_execution_decision"]["status"] == "NO_QUALIFIED_SIGNAL"
            and status["runner_interval_seconds"] == 2.0
            and status["last_run_once_duration_ms"] is not None
        )
        return show("run_once is called, events are generated, and WATCHLIST interval becomes 2s", passed, str(events))


async def verify_allowed_symbols_only_and_scan_report() -> bool:
    from backend.auto_validation.auto_validation_runner import AutoValidationRunner

    with tempfile.TemporaryDirectory() as tmp:
        signals = FakeSignals(
            [
                wait_signal("EURUSD", status_level="WAIT", signal_hash="eur-wait"),
                wait_signal("XAUUSD", status_level="WATCHLIST", signal_hash="xau-watch"),
                wait_signal("NIFTY50", status_level="WAIT", signal_hash="nifty-wait"),
            ]
        )
        service, _ = make_service(signals, state_path=Path(tmp) / "state.json")
        runner = AutoValidationRunner(service)
        service.start()
        await runner.run_tick()
        status = service.status()
        watched = status["current_signal_watched"]
        decision = status["last_execution_decision"]
        checked = decision["per_symbol_results"]
        passed = (
            watched["symbol"] in {"EURUSD", "XAUUSD"}
            and watched["symbol"] != "NIFTY50"
            and set(checked.keys()) == {"EURUSD", "XAUUSD"}
            and decision["EURUSD"]["status"] == "WAIT"
            and decision["XAUUSD"]["status"] == "WATCHLIST"
            and decision["last_checked_symbol"] == "XAUUSD"
            and decision["best_candidate_symbol"] == "XAUUSD"
            and "NIFTY50" not in decision["watched_symbols"]
            and "NIFTY50" not in decision["no_qualified_reason"]
        )
        return show("AUTO validation watches only allowed symbols and reports EURUSD/XAUUSD scan results", passed, str(decision))


async def verify_no_overlapping_run_once_calls() -> bool:
    from backend.auto_validation.auto_validation_runner import AutoValidationRunner

    class SlowService:
        def __init__(self) -> None:
            self.calls = 0
            self.events: list[dict[str, Any]] = []
            self.runner_state: dict[str, Any] = {}
            self.session = {"status": "RUNNING"}
            self.config = {"auto_validation_enabled": True}

        def should_auto_start_runner(self) -> bool:
            return True

        def watched_signal_is_watchlist(self) -> bool:
            return False

        def run_once(self) -> dict[str, Any]:
            self.calls += 1
            time.sleep(0.2)
            return {"status": "NO_QUALIFIED_SIGNAL"}

        def log_runner_error(self, message: str) -> None:
            self.events.append({"event": "RUNNER_ERROR", "details": {"error": message}})

        def update_runner_state(self, **updates: Any) -> None:
            self.runner_state.update(updates)

    service = SlowService()
    runner = AutoValidationRunner(service)  # type: ignore[arg-type]
    first = asyncio.create_task(runner.run_tick())
    await asyncio.sleep(0.02)
    second = await runner.run_tick()
    await first
    passed = service.calls == 1 and second["status"] == "SKIPPED" and second["reason"] == "RUN_ONCE_IN_PROGRESS"
    return show("Overlapping run_once calls are skipped", passed, str({"calls": service.calls, "second": second}))


async def verify_persisted_running_session_starts_on_backend_startup() -> bool:
    from backend.auto_validation.auto_validation_runner import AutoValidationRunner

    with tempfile.TemporaryDirectory() as tmp:
        state_path = Path(tmp) / "state.json"
        service, _ = make_service(state_path=state_path)
        service.start()

        restored, _ = make_service(state_path=state_path)
        runner = AutoValidationRunner(restored, default_interval_seconds=0.05, watchlist_interval_seconds=0.03)
        runner.start_if_running()
        await asyncio.sleep(0.1)
        passed = runner.is_active() and restored.session["status"] == "RUNNING" and any(event["event"] == "SIGNAL_EVALUATED" for event in restored.events)
        await runner.shutdown()
        return show("Persisted RUNNING session starts runner on backend startup", passed)


async def verify_runner_errors_logged() -> bool:
    from backend.auto_validation.auto_validation_runner import AutoValidationRunner

    with tempfile.TemporaryDirectory() as tmp:
        service, _ = make_service(FakeSignals(fail=True), state_path=Path(tmp) / "state.json")
        runner = AutoValidationRunner(service, default_interval_seconds=0.05, watchlist_interval_seconds=0.03)
        service.start()
        result = await runner.run_tick()
        events = [event["event"] for event in service.events]
        status = service.status()
        passed = result["status"] == "RUNNER_ERROR" and "RUNNER_ERROR" in events and status["last_runner_error"] == "signal provider failed"
        return show("Runner errors are logged and do not crash backend", passed, str(events))


def verify_code_wiring_and_dashboard() -> bool:
    service = SERVICE_PATH.read_text(encoding="utf-8")
    runner = RUNNER_PATH.read_text(encoding="utf-8")
    routes = ROUTES_PATH.read_text(encoding="utf-8")
    main = MAIN_PATH.read_text(encoding="utf-8")
    dashboard = DASHBOARD_PATH.read_text(encoding="utf-8")
    required = [
        "AutoValidationRunner",
        "auto_validation_runner.start()",
        "auto_validation_runner.stop()",
        "auto_validation_runner.start_if_running()",
        "await auto_validation_runner.shutdown()",
        "runner_active",
        "runner_last_tick_at",
        "runner_next_tick_at",
        "run_once_in_progress",
        "last_run_once_duration_ms",
        "last_runner_error",
        "RUNNER_ERROR",
        "Last Scan Time",
        "Next Scan Time",
        "Last Runner Error",
        "Watching",
        "Last Checked Symbol",
        "Best Candidate Symbol",
        "Why no symbol qualified",
        "per_symbol_results",
    ]
    missing = [item for item in required if item not in service + runner + routes + main + dashboard]
    return show("Runner route/status wiring and dashboard fields exist", not missing, ", ".join(missing))


def verify_no_unrestricted_order_send() -> bool:
    token = "mt5." + "order_send"
    matches = [
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in (PROJECT_ROOT / "backend").rglob("*.py")
        if token in path.read_text(encoding="utf-8", errors="ignore")
    ]
    allowed = ["backend/demo_execution/mt5_demo_executor.py", "backend/mt5_demo/guarded_demo_order_sender_service.py"]
    return show("No unrestricted mt5.order_send added", sorted(matches) == allowed, ", ".join(matches))


async def async_main() -> list[bool]:
    return [
        await verify_runner_lifecycle(),
        await verify_run_once_called_and_events_generated(),
        await verify_allowed_symbols_only_and_scan_report(),
        await verify_no_overlapping_run_once_calls(),
        await verify_persisted_running_session_starts_on_backend_startup(),
        await verify_runner_errors_logged(),
    ]


def main() -> int:
    print("Phase 22.2 AUTO Validation Runner Loop Verification")
    print("=" * 78)
    checks = asyncio.run(async_main())
    checks.extend([verify_code_wiring_and_dashboard(), verify_no_unrestricted_order_send()])
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
