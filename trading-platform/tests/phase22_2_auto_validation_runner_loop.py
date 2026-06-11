import asyncio
from datetime import datetime, timedelta, timezone
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
CLIENT_ENGINE_PATH = PROJECT_ROOT / "backend/strategy/client_signal_engine.py"
REAL_ENGINE_PATH = PROJECT_ROOT / "backend/strategy/real_signal_engine_service.py"


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
        "strategy_profile": "AUTO_VALIDATION",
        "strategy_components": {
            "liquidity_sweep": False,
            "bos": False,
            "choch": False,
            "fvg": True,
            "order_block": True,
            "session_valid": True,
        },
        "entry": None,
        "stop_loss": None,
        "take_profit": None,
        "risk_reward": None,
        "candle_source": {"broker_source": "VANTAGE_DEMO", "server": "VantageMarkets-Demo", "account_type": "DEMO"},
    }


def ready_signal(symbol: str = "XAUUSD", *, signal_hash: str = "runner-ready") -> dict[str, Any]:
    payload = wait_signal(symbol, status_level="READY", signal_hash=signal_hash)
    payload.update(
        {
            "signal": "BUY",
            "status_level": "READY_FOR_PREVIEW",
            "confidence": 82,
            "execution_status": "READY_FOR_PREVIEW",
            "risk_status": "APPROVED",
            "missing_requirements": [],
            "what_needs_to_happen_next": "Ready for guarded demo validation.",
            "entry": 2400.0 if symbol == "XAUUSD" else 1.1,
            "stop_loss": 2390.0 if symbol == "XAUUSD" else 1.09,
            "take_profit": 2420.0 if symbol == "XAUUSD" else 1.12,
            "risk_reward": 2.0,
        }
    )
    return payload


class FakeSignals:
    def __init__(self, signals: list[dict[str, Any]] | None = None, *, fail: bool = False) -> None:
        self.signals = signals or [wait_signal()]
        self.fail = fail
        self.requested_profiles: list[str] = []

    def current(self, record_history: bool = False) -> dict[str, Any]:
        if self.fail:
            raise RuntimeError("signal provider failed")
        return {"signals": self.signals}

    def signal_for_symbol(self, symbol: str, record_history: bool = False, strategy_profile: str = "PRODUCTION") -> dict[str, Any]:
        if self.fail:
            raise RuntimeError("signal provider failed")
        self.requested_profiles.append(strategy_profile)
        signal = dict(next((signal for signal in self.signals if signal.get("symbol") == symbol), wait_signal(symbol)))
        signal["strategy_profile"] = strategy_profile
        return signal


class RevalidatingSignals:
    def __init__(self, original: dict[str, Any], current: dict[str, Any]) -> None:
        self.original = original
        self.current = current
        self.calls: dict[str, int] = {}
        self.requested_profiles: list[str] = []

    def signal_for_symbol(self, symbol: str, record_history: bool = False, strategy_profile: str = "PRODUCTION") -> dict[str, Any]:
        self.requested_profiles.append(strategy_profile)
        if symbol != self.original.get("symbol"):
            return wait_signal(symbol, status_level="WAIT", signal_hash=f"{symbol.lower()}-wait")
        count = self.calls.get(symbol, 0)
        self.calls[symbol] = count + 1
        signal = dict(self.original if count == 0 else self.current)
        signal["strategy_profile"] = strategy_profile
        return signal


class FakeGuarded:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.market_data_service = self
        self.failed_ticks: set[str] = set()
        self.reject = False
        self.approval_blocked = False
        self.order_send_fail = False

    def get_symbol_tick(self, symbol: str) -> dict[str, Any]:
        if symbol in self.failed_ticks:
            return {"status": "SYMBOL_TICK_UNAVAILABLE", "spread": None}
        return {"status": "OK", "bid": 1.1, "ask": 1.2, "spread": 0.2}

    def send_test_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(payload)
        if self.approval_blocked:
            return {
                "status": "BLOCKED",
                "mt5_order_sent": False,
                "guarded_sender_used": False,
                "approval_workflow_status": "BLOCKED",
                "approval_workflow_passed": False,
                "guarded_sender_attempted": False,
                "order_send_attempted": False,
                "order_opened": False,
                "final_blocker": "APPROVAL_WORKFLOW_NOT_APPROVED",
                "rejection_code": "APPROVAL_WORKFLOW_NOT_APPROVED",
                "rejection_reason": "Approval workflow blocked the guarded demo order.",
                "failed_guard": "APPROVAL_WORKFLOW_NOT_APPROVED",
                "strategy_profile": payload.get("strategy_profile"),
            }
        if self.reject:
            return {
                "status": "BLOCKED",
                "mt5_order_sent": False,
                "guarded_sender_used": True,
                "approval_workflow_status": "APPROVED_FOR_FUTURE_SINGLE_DEMO_ORDER_TEST",
                "approval_workflow_passed": True,
                "guarded_sender_attempted": True,
                "order_send_attempted": False,
                "order_opened": False,
                "final_blocker": "TEST_SENDER_BLOCK",
                "rejection_code": "TEST_SENDER_BLOCK",
                "rejection_reason": "Test sender rejection.",
                "failed_guard": "TEST_SENDER_BLOCK",
                "strategy_profile": payload.get("strategy_profile"),
            }
        if self.order_send_fail:
            return {
                "status": "DEMO_ORDER_REJECTED",
                "mt5_order_sent": False,
                "guarded_sender_used": True,
                "approval_workflow_status": "APPROVED_FOR_FUTURE_SINGLE_DEMO_ORDER_TEST",
                "approval_workflow_passed": True,
                "guarded_sender_attempted": True,
                "order_send_attempted": True,
                "demo_order_attempted": True,
                "order_opened": False,
                "final_blocker": "MT5_RETCODE_REJECTED",
                "rejection_code": "MT5_RETCODE_REJECTED",
                "rejection_reason": "MT5 rejected the demo order.",
                "failed_guard": "MT5_RETCODE_REJECTED",
                "strategy_profile": payload.get("strategy_profile"),
                "retcode": "10030",
                "final_comment": "Rejected by test MT5 retcode.",
            }
        return {
            "status": "DEMO_ORDER_SENT",
            "mt5_order_sent": True,
            "guarded_sender_used": True,
            "ticket": "9101",
            "retcode": "10009",
            "approval_workflow_status": "APPROVED_FOR_FUTURE_SINGLE_DEMO_ORDER_TEST",
            "approval_workflow_passed": True,
            "guarded_sender_attempted": True,
            "order_send_attempted": True,
            "order_opened": True,
            "final_blocker": "",
        }


class FakeJournal:
    def __init__(self, trades: list[dict[str, Any]] | None = None) -> None:
        self.trades = trades or []

    def list_trades(self, limit: int = 100000) -> list[dict[str, Any]]:
        return self.trades[-limit:]

    def record_open_position(self, payload: dict[str, Any]) -> dict[str, Any]:
        ticket = str(payload.get("mt5_ticket") or payload.get("ticket") or "")
        existing = next((trade for trade in self.trades if str(trade.get("mt5_ticket") or "") == ticket and ticket), None)
        record = {**(existing or {}), **payload, "status": "OPEN", "result": "OPEN", "mt5_ticket": ticket}
        if existing is None:
            record.setdefault("trade_id", f"mt5_demo_{ticket}")
            self.trades.append(record)
        else:
            self.trades[self.trades.index(existing)] = record
        return record


class FakePositions:
    def __init__(self, positions: list[dict[str, Any]] | None = None) -> None:
        self.positions = positions or []

    def get_open_positions(self) -> dict[str, Any]:
        return {"positions": self.positions}

    def get_open_positions_by_symbol(self, symbol: str) -> dict[str, Any]:
        return {"positions": [item for item in self.positions if str(item.get("symbol") or "").upper() == symbol.upper()]}


class FakeAccount:
    def get_status(self) -> dict[str, Any]:
        return {"account_type": "DEMO", "server": "VantageMarkets-Demo", "login": "123", "terminal_running": True, "status": "CONNECTED"}


class FakeApprovalWorkflow:
    def run_workflow(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"approved_for_future_demo_order": True, "blockers": []}


class FakeVantageMarket:
    def __init__(self, tick: dict[str, Any] | None = None) -> None:
        self.tick = tick or {"symbol": "XAUUSD", "status": "OK", "bid": 2400.0, "ask": 2400.25, "spread": 0.25, "source": "VANTAGE_DEMO"}

    def get_symbol_tick(self, symbol: str) -> dict[str, Any]:
        return {**self.tick, "symbol": symbol}

    def get_xauusd_diagnostics(self) -> dict[str, Any]:
        return {"tick_available": True, "bid": self.tick.get("bid"), "ask": self.tick.get("ask"), "spread": self.tick.get("spread"), "source": "VANTAGE_DEMO", "readiness_result": "READY"}


class FakeVantageSender:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def send_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(payload)
        return {"status": "DEMO_ORDER_SENT", "mt5_order_sent": True, "guarded_sender_used": True, "strategy_profile": payload.get("strategy_profile")}


class FakeVantagePositions:
    def get_open_positions_by_symbol(self, symbol: str) -> dict[str, Any]:
        return {"positions": []}


class RevalidationSignalEngine:
    def __init__(self, signal: dict[str, Any]) -> None:
        self.signal = signal
        self.calls: list[tuple[str, str]] = []

    def generate_signal(self, symbol: str, strategy_profile: str = "PRODUCTION") -> dict[str, Any]:
        self.calls.append((symbol, strategy_profile))
        return {**self.signal, "symbol": symbol, "strategy_profile": strategy_profile}


def make_service(signals: FakeSignals | None = None, state_path: Path | None = None, positions: list[dict[str, Any]] | None = None, trades: list[dict[str, Any]] | None = None):
    from backend.auto_validation.auto_validation_service import AutoValidationService

    guarded = FakeGuarded()
    return (
        AutoValidationService(
            signal_provider=signals or FakeSignals(),
            guarded_execution_service=guarded,
            journal_service=FakeJournal(trades),
            position_service=FakePositions(positions),
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
            and status["session"]["signals_scanned"] == 2
            and status["session"]["signals_watchlist"] == 2
            and status["session"]["signals_ready_for_preview"] == 0
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
            and signals.requested_profiles == ["DEMO_COLLECTION", "DEMO_COLLECTION"]
        )
        return show("AUTO validation watches only allowed symbols and reports EURUSD/XAUUSD scan results", passed, str(decision))


async def verify_recoverable_market_data_failure_does_not_halt() -> bool:
    from backend.auto_validation.auto_validation_runner import AutoValidationRunner

    with tempfile.TemporaryDirectory() as tmp:
        signals = FakeSignals(
            [
                wait_signal("EURUSD", status_level="WATCHLIST", signal_hash="eur-watch"),
                ready_signal("XAUUSD", signal_hash="xau-ready"),
            ]
        )
        service, guarded = make_service(signals, state_path=Path(tmp) / "state.json")
        guarded.failed_ticks.add("XAUUSD")
        runner = AutoValidationRunner(service)
        service.start()
        await runner.run_tick()
        status = service.status()
        decision = status["last_execution_decision"]
        events = [event["event"] for event in service.events]
        passed = (
            service.session["status"] == "RUNNING"
            and status["mt5_health"]["status"] == "MT5_CONNECTED"
            and status["mt5_health"]["consecutive_failed_health_checks"] == 0
            and status["mt5_health"]["last_successful_tick_symbol"] == "EURUSD"
            and "TEMPORARY_MARKET_DATA_FAILURE" in events
            and "SYMBOL_TICK_UNAVAILABLE" in decision["XAUUSD"]["blockers"]
            and "MT5_DISCONNECTED" not in decision["XAUUSD"]["blockers"]
        )
        return show("Single-symbol tick failure is recoverable and does not halt AUTO validation", passed, str(status["mt5_health"]))


async def verify_auto_validation_profile_loosened_rules_fire_demo_order() -> bool:
    from backend.auto_validation.auto_validation_runner import AutoValidationRunner

    with tempfile.TemporaryDirectory() as tmp:
        relaxed = ready_signal("XAUUSD", signal_hash="xau-auto-validation-relaxed")
        relaxed.update(
            {
                "confidence": 68,
                "strategy_components": {
                    "liquidity_sweep": False,
                    "bos": False,
                    "choch": False,
                    "fvg": True,
                    "order_block": True,
                    "session_valid": True,
                },
                "quality_score": {"confidence": 68},
            }
        )
        signals = FakeSignals([relaxed])
        service, guarded = make_service(signals, state_path=Path(tmp) / "state.json")
        service.start({"strategy_profile": "AUTO_VALIDATION"})
        result = await AutoValidationRunner(service).run_tick()
        payload = guarded.calls[0] if guarded.calls else {}
        status = service.status()
        passed = (
            result["status"] == "ORDER_SENT"
            and len(guarded.calls) == 1
            and payload.get("strategy_profile") == "AUTO_VALIDATION"
            and payload.get("lot") == 0.01
            and payload.get("live_execution_enabled") is False
            and payload.get("broker_execution_enabled") is False
            and status["session"]["signals_scanned"] == 2
            and status["session"]["signals_ready_for_preview"] == 1
            and status["session"]["signals_sent_to_sender"] == 1
            and status["session"]["signals_blocked_by_sender"] == 0
            and status["session"]["orders_created"] == 1
            and signals.requested_profiles[:2] == ["AUTO_VALIDATION", "AUTO_VALIDATION"]
        )
        return show("AUTO_VALIDATION allows demo-only 68 confidence setup without BOS/liquidity hard gates", passed, str(payload))


async def verify_demo_collection_relaxed_directional_setup_opens() -> bool:
    from backend.auto_validation.auto_validation_runner import AutoValidationRunner

    with tempfile.TemporaryDirectory() as tmp:
        demo = ready_signal("XAUUSD", signal_hash="xau-demo-collection-open")
        demo.update(
            {
                "confidence": 58,
                "risk_reward": 1.2,
                "strategy_components": {
                    "liquidity_sweep": False,
                    "bos": False,
                    "choch": False,
                    "fvg": False,
                    "order_block": False,
                    "session_valid": False,
                },
                "quality_score": {"confidence": 58},
                "approval_audit": {
                    "strategy_profile": "DEMO_COLLECTION",
                    "relaxed_blockers": [
                        {"code": "FVG_MISSING"},
                        {"code": "ORDER_BLOCK_MISSING"},
                        {"code": "SESSION_INVALID"},
                    ],
                    "sl_tp_source": "DEMO_RISK_FALLBACK",
                },
                "sl_tp_source": "DEMO_RISK_FALLBACK",
                "demo_risk_model": {"model": "ATR_OR_FIXED_RISK", "min_rr": 1.2},
            }
        )
        signals = FakeSignals([demo])
        service, guarded = make_service(signals, state_path=Path(tmp) / "state.json")
        service.start()
        result = await AutoValidationRunner(service).run_tick()
        payload = guarded.calls[0] if guarded.calls else {}
        status = service.status()
        passed = (
            result["status"] == "ORDER_SENT"
            and status["config"]["strategy_profile"] == "DEMO_COLLECTION"
            and payload.get("strategy_profile") == "DEMO_COLLECTION"
            and payload.get("strategy_metadata", {}).get("sl_tp_source") == "DEMO_RISK_FALLBACK"
            and status["session"]["orders_created"] == 1
            and signals.requested_profiles[:2] == ["DEMO_COLLECTION", "DEMO_COLLECTION"]
        )
        return show("DEMO_COLLECTION relaxed directional setup can reach OPENED = 1", passed, str({"payload": payload, "session": status["session"]}))


async def verify_auto_validation_profile_remains_strict() -> bool:
    from backend.auto_validation.auto_validation_runner import AutoValidationRunner

    with tempfile.TemporaryDirectory() as tmp:
        strict = ready_signal("XAUUSD", signal_hash="xau-auto-validation-strict")
        strict.update(
            {
                "confidence": 68,
                "strategy_components": {
                    "liquidity_sweep": False,
                    "bos": False,
                    "choch": False,
                    "fvg": False,
                    "order_block": False,
                    "session_valid": False,
                },
            }
        )
        service, guarded = make_service(FakeSignals([strict]), state_path=Path(tmp) / "state.json")
        service.start({"strategy_profile": "AUTO_VALIDATION"})
        result = await AutoValidationRunner(service).run_tick()
        passed = (
            result["status"] == "BLOCKED"
            and "FVG_REQUIRED" in result["blockers"]
            and "ORDER_BLOCK_REQUIRED" in result["blockers"]
            and "SESSION_VALID_REQUIRED" in result["blockers"]
            and guarded.calls == []
            and service.status()["config"]["strategy_profile"] == "AUTO_VALIDATION"
        )
        return show("AUTO_VALIDATION remains strict when explicitly selected", passed, str(result))


def verify_real_engine_demo_collection_fallback_sl_tp() -> bool:
    from backend.strategy.real_signal_engine_service import RealSignalEngineService

    engine = RealSignalEngineService()
    candles = [{"open": 2398.0, "high": 2402.0, "low": 2396.0, "close": 2400.0} for _ in range(40)]
    plan = engine._demo_collection_trade_plan(  # type: ignore[attr-defined]
        "XAUUSD",
        "BUY",
        {"status": "OK", "ask": 2400.0, "bid": 2399.8, "spread": 0.2},
        candles,
        {},
    )
    passed = (
        plan.get("sl_tp_source") == "DEMO_RISK_FALLBACK"
        and plan.get("entry") == 2400.0
        and plan.get("stop_loss") < plan.get("entry") < plan.get("take_profit")
        and plan.get("risk_reward") >= 1.2
    )
    return show("DEMO_COLLECTION generates fallback SL/TP from real tick plus ATR/fixed risk model", passed, str(plan))


def _vantage_service_for_revalidation(current_signal: dict[str, Any]):
    from backend.mt5_demo.vantage_xauusd_demo_validation_service import VantageXAUUSDDemoValidationService

    sender = FakeVantageSender()
    service = VantageXAUUSDDemoValidationService(
        mt5_demo_service=FakeAccount(),
        market_data_service=FakeVantageMarket(),
        approval_workflow_service=FakeApprovalWorkflow(),
        guarded_sender_service=sender,
        position_sync_service=FakeVantagePositions(),
        lifecycle_service=object(),
        signal_engine_service=RevalidationSignalEngine(current_signal),
    )
    return service, sender


def _demo_collection_vantage_payload(side: str = "SELL", **overrides: Any) -> dict[str, Any]:
    payload = {
        "symbol": "XAUUSD",
        "side": side,
        "action": side,
        "lot": 0.01,
        "stop_loss": 2410.0 if side == "SELL" else 2390.0,
        "take_profit": 2380.0 if side == "SELL" else 2420.0,
        "risk_reward_ratio": 2.0,
        "signal_confidence": 68,
        "signal_hash": "demo-original",
        "signal_timestamp": datetime.now(timezone.utc).isoformat(),
        "strategy_profile": "DEMO_COLLECTION",
        "confirm": True,
        "live_execution_enabled": False,
        "broker_execution_enabled": False,
        "validation_session_id": "demo-validation-test",
    }
    payload.update(overrides)
    return payload


def verify_vantage_same_direction_minor_change_proceeds() -> bool:
    current = ready_signal("XAUUSD", signal_hash="demo-current-minor")
    current.update(
        {
            "signal": "SELL",
            "entry": 2399.5,
            "stop_loss": 2410.0,
            "take_profit": 2379.0,
            "risk_reward": 2.0,
            "confidence": 69,
            "strategy_profile": "DEMO_COLLECTION",
        }
    )
    service, sender = _vantage_service_for_revalidation(current)
    result = service.send_test_order(_demo_collection_vantage_payload("SELL", take_profit=2380.0))
    blockers = result.get("blocked_reasons") or result.get("blockers") or []
    passed = result["status"] == "DEMO_ORDER_SENT" and len(sender.calls) == 1 and "SIGNAL_DIRECTION_CHANGED" not in blockers
    return show("Vantage revalidation permits same-direction entry/TP hash drift", passed, str({"result": result, "sender_calls": sender.calls}))


def verify_vantage_buy_to_sell_direction_change_rejects() -> bool:
    current = ready_signal("XAUUSD", signal_hash="demo-current-sell")
    current.update({"signal": "SELL", "stop_loss": 2410.0, "take_profit": 2380.0, "risk_reward": 2.0, "confidence": 69, "strategy_profile": "DEMO_COLLECTION"})
    service, sender = _vantage_service_for_revalidation(current)
    result = service.send_test_order(_demo_collection_vantage_payload("BUY", stop_loss=2390.0, take_profit=2420.0))
    blockers = result.get("blocked_reasons") or result.get("blockers") or []
    passed = result["status"] == "BLOCKED" and "SIGNAL_DIRECTION_CHANGED" in blockers and sender.calls == []
    return show("Vantage revalidation rejects real BUY to SELL direction change", passed, str(result))


def verify_vantage_sell_to_buy_direction_change_rejects() -> bool:
    current = ready_signal("XAUUSD", signal_hash="demo-current-buy")
    current.update({"signal": "BUY", "stop_loss": 2390.0, "take_profit": 2420.0, "risk_reward": 2.0, "confidence": 69, "strategy_profile": "DEMO_COLLECTION"})
    service, sender = _vantage_service_for_revalidation(current)
    result = service.send_test_order(_demo_collection_vantage_payload("SELL"))
    blockers = result.get("blocked_reasons") or result.get("blockers") or []
    passed = result["status"] == "BLOCKED" and "SIGNAL_DIRECTION_CHANGED" in blockers and sender.calls == []
    return show("Vantage revalidation rejects real SELL to BUY direction change", passed, str(result))


async def verify_duplicate_same_active_signal_blocks() -> bool:
    from backend.auto_validation.auto_validation_runner import AutoValidationRunner

    with tempfile.TemporaryDirectory() as tmp:
        signals = FakeSignals([ready_signal("XAUUSD", signal_hash="xau-duplicate-active")])
        service, guarded = make_service(signals, state_path=Path(tmp) / "state.json")
        runner = AutoValidationRunner(service)
        service.start({"cooldown_after_trade_minutes": 0})
        first = await runner.run_tick()
        second = await runner.run_tick()
        duplicate = service.status()["last_duplicate_check"]
        passed = (
            first["status"] == "ORDER_SENT"
            and second["status"] == "BLOCKED"
            and "DUPLICATE_SIGNAL_BLOCKED" in second["blockers"]
            and duplicate["duplicate_source"] in {"same_active_signal_already_sent", "active_journal_record"}
            and duplicate["final_duplicate_decision"] is True
            and len(guarded.calls) == 1
        )
        return show("Repeated same active AUTO signal is blocked as duplicate", passed, str({"second": second, "duplicate": duplicate}))


async def verify_closed_historical_trade_does_not_block_duplicate_check() -> bool:
    from backend.auto_validation.auto_validation_runner import AutoValidationRunner

    with tempfile.TemporaryDirectory() as tmp:
        signal = ready_signal("XAUUSD", signal_hash="xau-closed-history")
        trades = [
            {
                "validation_session_id": "old-session",
                "symbol": "XAUUSD",
                "side": "BUY",
                "status": "CLOSED",
                "signal_hash": "xau-closed-history",
                "strategy_profile": "AUTO_VALIDATION",
            }
        ]
        service, guarded = make_service(FakeSignals([signal]), state_path=Path(tmp) / "state.json", trades=trades)
        service.start()
        result = await AutoValidationRunner(service).run_tick()
        duplicate = service.status()["last_duplicate_check"]
        passed = result["status"] == "ORDER_SENT" and len(guarded.calls) == 1 and duplicate["duplicate_source"] == "none" and duplicate["matching_journal_records"] == 0
        return show("Closed historical trade does not block new AUTO signal", passed, str(duplicate))


async def verify_failed_sender_attempt_does_not_create_duplicate() -> bool:
    from backend.auto_validation.auto_validation_runner import AutoValidationRunner

    with tempfile.TemporaryDirectory() as tmp:
        service, guarded = make_service(FakeSignals([ready_signal("XAUUSD", signal_hash="xau-failed-retry")]), state_path=Path(tmp) / "state.json")
        runner = AutoValidationRunner(service)
        service.start({"cooldown_after_trade_minutes": 0})
        guarded.reject = True
        first = await runner.run_tick()
        guarded.reject = False
        second = await runner.run_tick()
        passed = (
            first["status"] == "BLOCKED"
            and second["status"] == "ORDER_SENT"
            and service.status()["session"]["orders_created"] == 1
            and len(guarded.calls) == 2
        )
        return show("Blocked/failed sender attempt does not create duplicate", passed, str({"first": first, "second": second}))


async def verify_cooldown_is_separate_from_duplicate() -> bool:
    from backend.auto_validation.auto_validation_runner import AutoValidationRunner

    with tempfile.TemporaryDirectory() as tmp:
        first_signal = ready_signal("XAUUSD", signal_hash="xau-cooldown-one")
        second_signal = ready_signal("XAUUSD", signal_hash="xau-cooldown-two")
        signals = FakeSignals([first_signal])
        service, guarded = make_service(signals, state_path=Path(tmp) / "state.json")
        runner = AutoValidationRunner(service)
        service.start({"cooldown_after_trade_minutes": 15})
        first = await runner.run_tick()
        signals.signals = [second_signal]
        second = await runner.run_tick()
        duplicate = service.status()["last_duplicate_check"]
        passed = (
            first["status"] == "ORDER_SENT"
            and second["status"] == "BLOCKED"
            and "COOLDOWN_ACTIVE" in second["blockers"]
            and "DUPLICATE_SIGNAL_BLOCKED" not in second["blockers"]
            and duplicate["duplicate_source"] == "none"
            and duplicate["cooldown_active"] is True
            and len(guarded.calls) == 1
        )
        return show("Cooldown is reported separately from duplicate", passed, str({"second": second, "duplicate": duplicate}))


async def verify_open_position_blocks_duplicate() -> bool:
    from backend.auto_validation.auto_validation_runner import AutoValidationRunner

    with tempfile.TemporaryDirectory() as tmp:
        positions = [{"symbol": "XAUUSD", "ticket": "123", "volume": 0.01}]
        service, guarded = make_service(FakeSignals([ready_signal("XAUUSD", signal_hash="xau-open-position")]), state_path=Path(tmp) / "state.json", positions=positions)
        service.start()
        result = await AutoValidationRunner(service).run_tick()
        status = service.status()
        duplicate = status["last_duplicate_check"]
        session = status["session"]
        sync = status["open_position_sync"]
        passed = (
            result["status"] == "BLOCKED"
            and "DUPLICATE_SIGNAL_BLOCKED" in result["blockers"]
            and duplicate["duplicate_source"] == "open_mt5_position"
            and duplicate["open_positions_count"] == 1
            and session["current_open_trades"] == 1
            and session["open_trades"] == 1
            and session["total_trades"] == 1
            and session["opened"] == 1
            and session["orders_created"] == 1
            and sync["mt5_open_positions_detected"] == 1
            and sync["auto_owned_open_positions"] == 1
            and sync["unmatched_open_positions"] == 0
            and sync["open_position_tickets"] == ["123"]
            and guarded.calls == []
        )
        return show("Genuine open position blocks duplicate AUTO signal and syncs open telemetry", passed, str({"result": result, "duplicate": duplicate, "session": session, "sync": sync}))


async def verify_auto_validation_minor_hash_change_does_not_block() -> bool:
    from backend.auto_validation.auto_validation_runner import AutoValidationRunner

    with tempfile.TemporaryDirectory() as tmp:
        original = ready_signal("XAUUSD", signal_hash="xau-original-hash")
        original.update({"confidence": 68, "entry": 2400.0, "take_profit": 2420.0})
        current = dict(original)
        current.update({"signal_hash": "xau-minor-hash", "confidence": 69, "entry": 2400.5, "take_profit": 2421.0})
        signals = RevalidatingSignals(original, current)
        service, guarded = make_service(signals, state_path=Path(tmp) / "state.json")
        service.start()
        result = await AutoValidationRunner(service).run_tick()
        events = [event["event"] for event in service.events]
        audit = service.status()["last_hash_change_audit"]
        passed = (
            result["status"] == "ORDER_SENT"
            and len(guarded.calls) == 1
            and "HASH_CHANGE_MINOR" in events
            and "SIGNAL_HASH_CHANGED" not in events
            and audit["event"] == "HASH_CHANGE_MINOR"
            and audit["minor_change"] is True
            and audit["material_reasons"] == []
        )
        return show("AUTO_VALIDATION minor entry/TP/confidence hash drift does not block", passed, str({"events": events, "audit": audit}))


async def verify_auto_validation_material_hash_change_blocks() -> bool:
    from backend.auto_validation.auto_validation_runner import AutoValidationRunner

    with tempfile.TemporaryDirectory() as tmp:
        original = ready_signal("XAUUSD", signal_hash="xau-original-material")
        current = dict(original)
        current.update({"signal_hash": "xau-material-hash", "stop_loss": 2388.0})
        signals = RevalidatingSignals(original, current)
        service, guarded = make_service(signals, state_path=Path(tmp) / "state.json")
        service.start()
        result = await AutoValidationRunner(service).run_tick()
        events = [event["event"] for event in service.events]
        audit = service.status()["last_hash_change_audit"]
        passed = (
            result["status"] == "BLOCKED"
            and guarded.calls == []
            and "SIGNAL_HASH_CHANGED" in events
            and "STOP_LOSS_CHANGED" in audit["material_reasons"]
            and audit["event"] == "SIGNAL_HASH_CHANGED"
            and audit["minor_change"] is False
        )
        return show("AUTO_VALIDATION material stop-loss hash change blocks", passed, str({"events": events, "audit": audit}))


async def verify_sender_rejection_does_not_halt_and_records_diagnostics() -> bool:
    from backend.auto_validation.auto_validation_runner import AutoValidationRunner

    with tempfile.TemporaryDirectory() as tmp:
        signals = FakeSignals([ready_signal("XAUUSD", signal_hash="xau-sender-reject")])
        service, guarded = make_service(signals, state_path=Path(tmp) / "state.json")
        guarded.reject = True
        service.start()
        result = await AutoValidationRunner(service).run_tick()
        status = service.status()
        rejection = status["last_sender_rejection"]
        summary = service.post_sender_execution_summary()
        timeline = summary["latest_timeline"]
        events = [event["event"] for event in service.events]
        passed = (
            result["status"] == "BLOCKED"
            and service.session["status"] == "RUNNING"
            and "GUARDED_SENDER_REJECTED" in events
            and "POST_SENDER_EXECUTION_TRACE" in events
            and status["session"]["signals_sent_to_sender"] == 1
            and status["session"]["signals_blocked_by_sender"] == 1
            and status["session"]["orders_created"] == 0
            and summary["WRAPPER_SUBMITTED"] == 1
            and summary["APPROVAL_WORKFLOW_PASSED"] == 1
            and summary["SENT"] == 1
            and summary["GUARDED_SENDER_ATTEMPTED"] == 1
            and summary["ORDER_SEND_ATTEMPTED"] == 0
            and summary["ORDER_SEND_FAILED"] == 0
            and summary["OPENED"] == 0
            and summary["BLOCKED"] == 1
            and summary["dominant_blocker"]["reason"] == "TEST_SENDER_BLOCK"
            and timeline["signal_id"] == "xau-sender-reject"
            and timeline["sender_decision"] == "BLOCKED"
            and timeline["final_rejection_reason"] == "TEST_SENDER_BLOCK"
            and rejection["rejection_code"] == "TEST_SENDER_BLOCK"
            and rejection["failed_guard"] == "TEST_SENDER_BLOCK"
        )
        return show("Sender rejection records diagnostics, post-SENT timeline, and does not HALT_RISK", passed, str({"result": result, "rejection": rejection, "summary": summary, "events": events}))


async def verify_wrapper_submitted_approval_blocked_not_guarded_attempted() -> bool:
    from backend.auto_validation.auto_validation_runner import AutoValidationRunner

    with tempfile.TemporaryDirectory() as tmp:
        signals = FakeSignals([ready_signal("XAUUSD", signal_hash="xau-approval-blocked")])
        service, guarded = make_service(signals, state_path=Path(tmp) / "state.json")
        guarded.approval_blocked = True
        service.start()
        result = await AutoValidationRunner(service).run_tick()
        summary = service.post_sender_execution_summary()
        passed = (
            result["status"] == "BLOCKED"
            and summary["WRAPPER_SUBMITTED"] == 1
            and summary["APPROVAL_WORKFLOW_PASSED"] == 0
            and summary["GUARDED_SENDER_ATTEMPTED"] == 0
            and summary["SENT"] == 0
            and summary["ORDER_SEND_ATTEMPTED"] == 0
            and summary["OPENED"] == 0
            and summary["BLOCKED"] == 1
            and summary["dominant_blocker"]["reason"] == "APPROVAL_WORKFLOW_NOT_APPROVED"
        )
        return show("Wrapper submitted but approval blocked does not count as guarded sender attempted", passed, str({"result": result, "summary": summary}))


async def verify_order_send_attempt_failure_counter() -> bool:
    from backend.auto_validation.auto_validation_runner import AutoValidationRunner

    with tempfile.TemporaryDirectory() as tmp:
        signals = FakeSignals([ready_signal("XAUUSD", signal_hash="xau-order-send-failed")])
        service, guarded = make_service(signals, state_path=Path(tmp) / "state.json")
        guarded.order_send_fail = True
        service.start()
        result = await AutoValidationRunner(service).run_tick()
        summary = service.post_sender_execution_summary()
        passed = (
            result["status"] == "BLOCKED"
            and summary["WRAPPER_SUBMITTED"] == 1
            and summary["APPROVAL_WORKFLOW_PASSED"] == 1
            and summary["GUARDED_SENDER_ATTEMPTED"] == 1
            and summary["SENT"] == 1
            and summary["ORDER_SEND_ATTEMPTED"] == 1
            and summary["ORDER_SEND_FAILED"] == 1
            and summary["OPENED"] == 0
            and summary["dominant_blocker"]["reason"] == "MT5_RETCODE_REJECTED"
        )
        return show("MT5 order_send attempt increments attempted and failed counters", passed, str({"result": result, "summary": summary}))


async def verify_status_reconciles_open_mt5_positions_into_opened_counter() -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        trade = {
            "validation_session_id": "placeholder",
            "trade_id": "mt5_demo_9001",
            "status": "SENT",
            "result": "OPEN",
            "symbol": "XAUUSD",
            "side": "BUY",
            "lot": 0.01,
            "mt5_ticket": "9001",
            "strategy_profile": "DEMO_COLLECTION",
        }
        position = {
            "ticket": "9001",
            "symbol": "XAUUSD",
            "side": "BUY",
            "lot": 0.01,
            "entry_price": 2400.0,
            "stop_loss": 2390.0,
            "take_profit": 2420.0,
            "floating_pnl": 12.5,
        }
        service, _ = make_service(FakeSignals([wait_signal("XAUUSD")]), state_path=Path(tmp) / "state.json", positions=[position], trades=[trade])
        service.start()
        trade["validation_session_id"] = service.session["session_id"]
        status = service.status()
        session = status["session"]
        journal_trade = service.journal_service.trades[0]
        passed = (
            session["opened"] == 1
            and session["orders_created"] == 1
            and session["current_open_trades"] == 1
            and session["open_trades"] == 1
            and session["current_closed_trades"] == 0
            and session["total_trades"] == 1
            and session["wins"] == 0
            and session["losses"] == 0
            and session["net_pnl"] == 0
            and journal_trade["status"] == "OPEN"
            and journal_trade["mt5_ticket"] == "9001"
            and status["open_position_sync"]["mt5_open_positions_detected"] == 1
            and status["open_position_sync"]["auto_owned_open_positions"] == 1
            and status["open_position_sync"]["open_position_tickets"] == ["9001"]
        )
        return show("Status reconciles AUTO-owned MT5 open positions into opened counter without closed metrics", passed, str({"session": session, "journal": journal_trade}))


def verify_production_profile_stays_strict() -> bool:
    from backend.strategy.client_signal_engine import ClientSignalEngine

    class RecordingRealSignalEngine:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def generate_signal(self, symbol: str, strategy_profile: str = "PRODUCTION") -> dict[str, Any]:
            self.calls.append(strategy_profile)
            confidence = 68
            return {
                "symbol": symbol,
                "signal": "WAIT",
                "status_level": "WATCHLIST",
                "confidence": confidence,
                "risk_status": "REJECTED",
                "execution_status": "WAITING",
                "missing_requirements": [{"code": "CONFIDENCE_GAP", "gap": 75 - confidence}],
                "strategy_profile": strategy_profile,
                "simulation_only": True,
                "live_execution_enabled": False,
                "broker_execution_enabled": False,
            }

        def status(self) -> dict[str, Any]:
            return {"strategy_profiles": {"PRODUCTION": {"min_confidence": 75}}}

    class NoopHistory:
        def record(self, signal: dict[str, Any]) -> None:
            return None

        def history(self, limit: int = 500) -> list[dict[str, Any]]:
            return []

        def history_for_symbol(self, symbol: str, limit: int = 100) -> list[dict[str, Any]]:
            return []

    real = RecordingRealSignalEngine()
    engine = ClientSignalEngine(real_signal_service=real, history_service=NoopHistory())  # type: ignore[arg-type]
    signal = engine.signal_for_symbol("XAUUSD", record_history=False)
    passed = real.calls == ["PRODUCTION"] and signal["strategy_profile"] == "PRODUCTION" and signal["signal"] == "WAIT"
    return show("Production client signal path still uses PRODUCTION profile by default", passed, str({"calls": real.calls, "signal": signal}))


def verify_journal_stores_strategy_profile() -> bool:
    from backend.trade_journal.persistent_trade_journal_service import PersistentTradeJournalService

    with tempfile.TemporaryDirectory() as tmp:
        journal = PersistentTradeJournalService(Path(tmp) / "journal.json")
        record = journal.record_order_sent(
            {
                "trade_id": "profile-test",
                "symbol": "XAUUSD",
                "side": "BUY",
                "lot": 0.01,
                "strategy_profile": "AUTO_VALIDATION",
                "strategy_metadata": {"strategy_profile": "AUTO_VALIDATION"},
            }
        )
        passed = record.get("strategy_profile") == "AUTO_VALIDATION"
        return show("Journal stores strategy_profile", passed, str(record))


def verify_guarded_sender_auto_validation_xauusd_guard_accepts() -> bool:
    from backend.mt5_demo.guarded_demo_order_sender_service import GuardedDemoOrderSenderService

    class DemoAccount:
        def get_status(self) -> dict[str, Any]:
            return {"status": "CONNECTED", "environment": "DEMO", "account_type": "DEMO", "server": "VantageMarkets-Demo", "login": "123"}

    class Approved:
        def get_latest(self) -> dict[str, Any]:
            return {"approved_for_future_demo_order": True, "validation_passed": True, "simulation_passed": True, "overall_status": "READY"}

        def get_latest_approval(self) -> dict[str, Any]:
            return {"approved_for_future_demo_order": True}

        def get_latest_audit(self) -> dict[str, Any]:
            return {"overall_status": "READY"}

    deps = Approved()
    sender = GuardedDemoOrderSenderService(DemoAccount(), deps, deps, deps, deps, deps, deps)
    payload = {
        "environment": "DEMO",
        "symbol": "XAUUSD",
        "action": "SELL",
        "lot": 0.01,
        "entry_price": 2400.0,
        "stop_loss": 2410.0,
        "take_profit": 2380.0,
        "manual_confirmation": True,
        "acknowledge_demo_only": True,
        "acknowledge_no_live_trading": True,
        "acknowledge_single_trade_only": True,
        "live_execution_enabled": False,
        "broker_execution_enabled": False,
        "broker_source": "VANTAGE_DEMO",
        "strategy_profile": "AUTO_VALIDATION",
        "signal_confidence": 84,
        "risk_reward_ratio": 2.0,
    }
    result = sender.prepare_order(payload)
    passed = result["status"] == "PREPARED_BUT_NOT_SENT" and result["blockers"] == [] and result["strategy_profile"] == "AUTO_VALIDATION"
    return show("Guarded sender allows valid AUTO_VALIDATION XAUUSD Vantage demo guard path", passed, str(result))


async def verify_mt5_disconnect_requires_three_failed_health_checks() -> bool:
    from backend.auto_validation.auto_validation_runner import AutoValidationRunner

    class DisconnectedAccount:
        def get_status(self) -> dict[str, Any]:
            return {"account_type": "DEMO", "server": "", "login": "", "terminal_running": False, "status": "NOT_CONNECTED"}

    with tempfile.TemporaryDirectory() as tmp:
        service, guarded = make_service(FakeSignals([wait_signal("XAUUSD", status_level="WATCHLIST")]), state_path=Path(tmp) / "state.json")
        guarded.failed_ticks.update({"EURUSD", "XAUUSD"})
        service.mt5_demo_service = DisconnectedAccount()
        runner = AutoValidationRunner(service)
        service.start()
        await runner.run_tick()
        first = service.status()["mt5_health"]
        await runner.run_tick()
        second = service.status()["mt5_health"]
        await runner.run_tick()
        third = service.status()["mt5_health"]
        passed = (
            first["status"] != "MT5_DISCONNECTED"
            and second["status"] != "MT5_DISCONNECTED"
            and third["status"] == "MT5_DISCONNECTED"
            and third["consecutive_failed_health_checks"] == 3
            and service.session["status"] == "WAITING_FOR_MT5_RECONNECT"
            and guarded.calls == []
        )
        return show("MT5 disconnect pauses for reconnect after 3 failed health checks without orders", passed, str({"health": third, "session": service.session}))


async def verify_mt5_reconnect_auto_resumes_and_uses_10s_interval() -> bool:
    from backend.auto_validation.auto_validation_runner import AutoValidationRunner

    class MutableAccount:
        connected = False

        def get_status(self) -> dict[str, Any]:
            if self.connected:
                return {"account_type": "DEMO", "server": "VantageMarkets-Demo", "login": "123", "terminal_running": True, "status": "CONNECTED"}
            return {"account_type": "DEMO", "server": "", "login": "", "terminal_running": False, "status": "NOT_CONNECTED"}

    with tempfile.TemporaryDirectory() as tmp:
        service, guarded = make_service(FakeSignals([wait_signal("XAUUSD", status_level="WATCHLIST", signal_hash="xau-reconnect")]), state_path=Path(tmp) / "state.json")
        account = MutableAccount()
        service.mt5_demo_service = account
        guarded.failed_ticks.update({"EURUSD", "XAUUSD"})
        runner = AutoValidationRunner(service)
        service.start()
        await runner.run_tick()
        await runner.run_tick()
        await runner.run_tick()
        waiting = service.status()
        waiting_ok = waiting["session"]["status"] == "WAITING_FOR_MT5_RECONNECT" and waiting["runner_interval_seconds"] == 10.0

        account.connected = True
        guarded.failed_ticks.clear()
        await runner.run_tick()
        events = [event["event"] for event in service.events]
        status = service.status()
        passed = (
            waiting_ok
            and status["session"]["status"] == "RUNNING"
            and "MT5_RECONNECTED" in events
            and status["mt5_health"]["status"] == "MT5_CONNECTED"
            and guarded.calls == []
        )
        return show("MT5 reconnect auto-resumes RUNNING and reconnect polling uses 10s interval", passed, str({"events": events[-5:], "session": status["session"]}))


async def verify_mt5_disconnect_timeout_halts_only_after_timeout() -> bool:
    from backend.auto_validation.auto_validation_runner import AutoValidationRunner

    class DisconnectedAccount:
        def get_status(self) -> dict[str, Any]:
            return {"account_type": "DEMO", "server": "", "login": "", "terminal_running": False, "status": "NOT_CONNECTED"}

    with tempfile.TemporaryDirectory() as tmp:
        service, guarded = make_service(FakeSignals([ready_signal("XAUUSD", signal_hash="xau-timeout")]), state_path=Path(tmp) / "state.json")
        guarded.failed_ticks.update({"EURUSD", "XAUUSD"})
        service.mt5_demo_service = DisconnectedAccount()
        service.start({"mt5_disconnect_timeout_seconds": 1})
        runner = AutoValidationRunner(service)
        await runner.run_tick()
        await runner.run_tick()
        await runner.run_tick()
        waiting = service.session["status"] == "WAITING_FOR_MT5_RECONNECT"
        service.session["last_mt5_disconnect_at"] = (datetime.now(timezone.utc) - timedelta(seconds=2)).isoformat()
        await runner.run_tick()
        passed = (
            waiting
            and service.session["status"] == "HALTED_RISK"
            and service.session["reason_stopped"] == "MT5_DISCONNECT_TIMEOUT"
            and guarded.calls == []
        )
        return show("MT5 disconnect becomes HALTED_RISK only after configurable timeout", passed, str(service.session))


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

    class FailingService:
        def __init__(self) -> None:
            self.events: list[dict[str, Any]] = []
            self.runner_state: dict[str, Any] = {}
            self.session = {"status": "RUNNING"}
            self.config = {"auto_validation_enabled": True}

        def should_auto_start_runner(self) -> bool:
            return True

        def watched_signal_is_watchlist(self) -> bool:
            return False

        def waiting_for_mt5_reconnect(self) -> bool:
            return False

        def run_once(self) -> dict[str, Any]:
            raise RuntimeError("run_once failed")

        def log_runner_error(self, message: str) -> None:
            self.events.append({"event": "RUNNER_ERROR", "details": {"error": message}})

        def update_runner_state(self, **updates: Any) -> None:
            self.runner_state.update(updates)

    service = FailingService()
    runner = AutoValidationRunner(service)  # type: ignore[arg-type]
    result = await runner.run_tick()
    events = [event["event"] for event in service.events]
    passed = result["status"] == "RUNNER_ERROR" and "RUNNER_ERROR" in events and service.runner_state.get("last_runner_error") == "run_once failed"
    return show("Runner errors are logged and do not crash backend", passed, str(events))


def verify_code_wiring_and_dashboard() -> bool:
    service = SERVICE_PATH.read_text(encoding="utf-8")
    runner = RUNNER_PATH.read_text(encoding="utf-8")
    routes = ROUTES_PATH.read_text(encoding="utf-8")
    main = MAIN_PATH.read_text(encoding="utf-8")
    dashboard = DASHBOARD_PATH.read_text(encoding="utf-8")
    client_engine = CLIENT_ENGINE_PATH.read_text(encoding="utf-8")
    real_engine = REAL_ENGINE_PATH.read_text(encoding="utf-8")
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
        "Execution Funnel",
        "signals_scanned",
        "signals_wait",
        "signals_watchlist",
        "signals_ready_for_preview",
        "signals_sent_to_sender",
        "signals_blocked_by_sender",
        "orders_created",
        "wrapper_submitted",
        "approval_workflow_passed",
        "guarded_sender_attempted",
        "opened",
        "post_sender_execution_summary",
        "execution_timelines",
        "POST_SENDER_EXECUTION_TRACE",
        "Wrapper Submitted",
        "Approval Passed",
        "Guarded Sender Attempted",
        "ORDER_SEND_ATTEMPTED",
        "ORDER_SEND_FAILED",
        "dominant_blocker",
        "Last Sender Rejection",
        "rejection_code",
        "rejection_reason",
        "failed_guard",
        "Last Duplicate Check",
        "duplicate_key",
        "duplicate_source",
        "open_positions_count",
        "pending_orders_count",
        "matching_journal_records",
        "cooldown_active",
        "final_duplicate_decision",
        "Strategy Profile",
        "HASH_CHANGE_MINOR",
        "AUTO_VALIDATION",
        "DEMO_COLLECTION",
        "SL/TP Source",
        "Advisory Blockers",
        "DEMO_RISK_FALLBACK",
        "relaxed_blockers",
        "strategy_profile",
        "auto_validation_confidence = 65",
    ]
    missing = [item for item in required if item not in service + runner + routes + main + dashboard + client_engine + real_engine]
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
        await verify_recoverable_market_data_failure_does_not_halt(),
        await verify_auto_validation_profile_loosened_rules_fire_demo_order(),
        await verify_demo_collection_relaxed_directional_setup_opens(),
        await verify_auto_validation_profile_remains_strict(),
        await verify_duplicate_same_active_signal_blocks(),
        await verify_closed_historical_trade_does_not_block_duplicate_check(),
        await verify_failed_sender_attempt_does_not_create_duplicate(),
        await verify_cooldown_is_separate_from_duplicate(),
        await verify_open_position_blocks_duplicate(),
        await verify_auto_validation_minor_hash_change_does_not_block(),
        await verify_auto_validation_material_hash_change_blocks(),
        await verify_sender_rejection_does_not_halt_and_records_diagnostics(),
        await verify_wrapper_submitted_approval_blocked_not_guarded_attempted(),
        await verify_order_send_attempt_failure_counter(),
        await verify_status_reconciles_open_mt5_positions_into_opened_counter(),
        await verify_mt5_disconnect_requires_three_failed_health_checks(),
        await verify_mt5_reconnect_auto_resumes_and_uses_10s_interval(),
        await verify_mt5_disconnect_timeout_halts_only_after_timeout(),
        await verify_no_overlapping_run_once_calls(),
        await verify_persisted_running_session_starts_on_backend_startup(),
        await verify_runner_errors_logged(),
    ]


def main() -> int:
    print("Phase 22.2 AUTO Validation Runner Loop Verification")
    print("=" * 78)
    checks = asyncio.run(async_main())
    checks.extend([
        verify_production_profile_stays_strict(),
        verify_real_engine_demo_collection_fallback_sl_tp(),
        verify_vantage_same_direction_minor_change_proceeds(),
        verify_vantage_buy_to_sell_direction_change_rejects(),
        verify_vantage_sell_to_buy_direction_change_rejects(),
        verify_journal_stores_strategy_profile(),
        verify_guarded_sender_auto_validation_xauusd_guard_accepts(),
        verify_code_wiring_and_dashboard(),
        verify_no_unrestricted_order_send(),
    ])
    print("=" * 78)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
