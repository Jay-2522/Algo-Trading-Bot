from __future__ import annotations

from datetime import datetime, timedelta, timezone
import copy
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE_PATH = PROJECT_ROOT / "data" / "auto_validation" / "session_state.json"


class AutoValidationService:
    """Controlled 30-trade demo validation runner using the existing guarded sender only."""

    def __init__(
        self,
        signal_provider: Any | None = None,
        guarded_execution_service: Any | None = None,
        journal_service: Any | None = None,
        position_service: Any | None = None,
        mt5_demo_service: Any | None = None,
        state_path: Path | None = None,
    ) -> None:
        self.signal_provider = signal_provider
        self.guarded_execution_service = guarded_execution_service
        self.journal_service = journal_service
        self.position_service = position_service
        self.mt5_demo_service = mt5_demo_service
        self.state_path = state_path or DEFAULT_STATE_PATH
        self.config = self._default_config()
        self.session = self._empty_session()
        self.events: list[dict[str, Any]] = []
        self.runner_state = self._empty_runner_state()
        self._seen_signal_hashes: set[str] = set()
        self._last_trade_time: datetime | None = None
        self._last_execution_decision: dict[str, Any] | None = None
        self._current_signal_watched: dict[str, Any] | None = None
        self._load_state()

    def status(self) -> dict[str, Any]:
        self._refresh_session_metrics()
        self._clear_disallowed_watched_signal()
        return {
            "status": "READY",
            "mode": self.session["status"],
            "config": dict(self.config),
            "session": dict(self.session),
            "current_signal_watched": copy.deepcopy(self._current_signal_watched),
            "last_execution_decision": copy.deepcopy(self._last_execution_decision),
            "blocked_reasons": self._last_execution_decision.get("blockers", []) if isinstance(self._last_execution_decision, dict) else [],
            "next_eligible_time": self._next_eligible_time(),
            "events": self.events[-50:],
            **self.runner_state,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }

    def start(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        self.config = {**self.config, **self._safe_config(payload)}
        self.config["auto_validation_enabled"] = True
        self.session = {
            **self._empty_session(),
            "session_id": f"auto-validation-{uuid4()}",
            "started_at": self._timestamp(),
            "status": "RUNNING",
            "target_closed_trades": int(self.config["target_closed_trades"]),
        }
        self._seen_signal_hashes = set()
        self._last_trade_time = None
        self._last_execution_decision = None
        self._log("SESSION_STARTED", {"session_id": self.session["session_id"]})
        self._save_state()
        return self.status()

    def pause(self) -> dict[str, Any]:
        if self.session["status"] == "RUNNING":
            self.session["status"] = "PAUSED"
            self._log("SESSION_PAUSED")
            self._save_state()
        return self.status()

    def resume(self) -> dict[str, Any]:
        if self.session["status"] == "PAUSED":
            self.session["status"] = "RUNNING"
            self._log("SESSION_RESUMED")
            self._save_state()
        return self.status()

    def stop(self, reason: str = "Stopped manually.") -> dict[str, Any]:
        if self.session["status"] in {"RUNNING", "PAUSED"}:
            self.session["status"] = "STOPPED"
            self.session["stopped_at"] = self._timestamp()
            self.session["reason_stopped"] = reason
            self.config["auto_validation_enabled"] = False
            self._log("SESSION_STOPPED", {"reason": reason})
            self._save_state()
        return self.status()

    def emergency_stop(self) -> dict[str, Any]:
        return self._halt("EMERGENCY_STOP")

    def trades(self) -> list[dict[str, Any]]:
        session_id = self.session.get("session_id")
        if not session_id or self.journal_service is None:
            return []
        return [trade for trade in self.journal_service.list_trades(limit=100000) if trade.get("validation_session_id") == session_id]

    def summary(self) -> dict[str, Any]:
        self._refresh_session_metrics()
        return dict(self.session)

    def run_once(self, signals: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        if self.session["status"] != "RUNNING" or self.config["auto_validation_enabled"] is not True:
            return self._decision("IDLE", ["AUTO_VALIDATION_NOT_RUNNING"])
        self._refresh_session_metrics()
        halt = self._risk_halt_reason()
        if halt:
            return self._halt(halt)
        signals = self._allowed_signals(signals if signals is not None else self._load_signals())
        checked = [self._checked_symbol_result(signal) for signal in signals]
        best_candidate = self._best_candidate(checked)
        for signal in signals:
            self._current_signal_watched = signal
            self._log("SIGNAL_EVALUATED", {"symbol": signal.get("symbol"), "signal_hash": signal.get("signal_hash")})
            if not self._ready(signal):
                continue
            decision = self._execute_signal(signal)
            decision.update(self._scan_context(checked, signal))
            self._last_execution_decision = decision
            self._save_state()
            if decision["status"] in {"ORDER_SENT", "HALTED_RISK", "BLOCKED"}:
                return decision
        decision = self._decision("NO_QUALIFIED_SIGNAL", ["NO_READY_APPROVED_SIGNAL"], extra=self._scan_context(checked, best_candidate))
        self._log("NO_QUALIFIED_SIGNAL", decision)
        return decision

    def _execute_signal(self, signal: dict[str, Any]) -> dict[str, Any]:
        blockers = self._validate_signal(signal)
        if blockers:
            event = "RISK_HALT_TRIGGERED" if self._halt_blocker(blockers) else "SIGNAL_BLOCKED"
            self._log(event, {"blockers": blockers, "signal_hash": signal.get("signal_hash")})
            if self._halt_blocker(blockers):
                return self._halt(blockers[0])
            return self._decision("BLOCKED", blockers, signal)

        service = self.guarded_execution_service
        if service is None:
            return self._halt("GUARDED_SENDER_UNAVAILABLE")
        payload = self._guarded_payload(signal)
        result = service.send_test_order(payload)
        sent = result.get("status") == "DEMO_ORDER_SENT" and result.get("mt5_order_sent") is True
        if not sent:
            self._log("ORDER_REJECTED", {"sender_result": result})
            return self._halt("GUARDED_SENDER_REJECTED")
        self._seen_signal_hashes.add(str(signal.get("signal_hash") or ""))
        self._last_trade_time = datetime.now(timezone.utc)
        decision = self._decision("ORDER_SENT", [], signal, {"sender_result": result, "guarded_sender_used": True, "mt5_order_sent": True})
        self._log("ORDER_SENT", decision)
        self._refresh_session_metrics()
        self._save_state()
        return decision

    def _validate_signal(self, signal: dict[str, Any]) -> list[str]:
        blockers: list[str] = []
        config = self.config
        symbol = str(signal.get("symbol") or "").upper()
        signal_hash = str(signal.get("signal_hash") or "")
        account = self._account_status(signal)
        tick = self._tick(symbol)
        current = self._current_signal(symbol)
        open_positions = self._open_positions()

        if account.get("account_type") != config["account_type_required"]:
            blockers.append("LIVE_ACCOUNT_DETECTED" if account.get("account_type") == "LIVE" else "DEMO_ACCOUNT_REQUIRED")
        if self._broker_detected(account, signal) != config["broker_required"]:
            blockers.append("NON_VANTAGE_BROKER_DETECTED")
        if symbol not in set(config["allowed_symbols"]):
            blockers.append("SYMBOL_NOT_ALLOWED")
        if float(config["lot_size"]) > 0.01:
            blockers.append("LOT_SIZE_EXCEEDS_0_01")
        if signal.get("execution_status") != "READY_FOR_PREVIEW" or signal.get("risk_status") != "APPROVED":
            blockers.append("SIGNAL_NOT_READY_APPROVED")
        if self._number(signal.get("confidence"), 0) < float(config["min_confidence"]):
            blockers.append("CONFIDENCE_BELOW_MINIMUM")
        if self._number(signal.get("risk_reward"), 0) < float(config["min_rr"]):
            blockers.append("RR_BELOW_MINIMUM")
        if config["require_sl_tp"] and not all(self._number(signal.get(key), 0) > 0 for key in ["entry", "stop_loss", "take_profit"]):
            blockers.append("SL_TP_REQUIRED")
        if signal_hash and signal_hash in self._seen_signal_hashes:
            blockers.append("DUPLICATE_SIGNAL_BLOCKED")
        if len(open_positions) >= int(config["max_open_trades_total"]):
            blockers.append("MAX_OPEN_TRADES_TOTAL_REACHED")
        if len([item for item in open_positions if str(item.get("symbol") or "").upper() == symbol]) >= int(config["max_open_trades_per_symbol"]):
            blockers.append("MAX_OPEN_TRADES_PER_SYMBOL_REACHED")
        if self._daily_trade_count() >= int(config["max_daily_trades"]):
            blockers.append("MAX_DAILY_TRADE_LIMIT_REACHED")
        if self._cooldown_active():
            blockers.append("COOLDOWN_ACTIVE")
        if tick.get("status") not in {"OK", "TICK_AVAILABLE_DIRECT"}:
            blockers.append("MT5_DISCONNECT_DETECTED")
        if tick.get("spread") is None:
            blockers.append("SPREAD_UNAVAILABLE")
        if current is not None and current.get("signal_hash") != signal.get("signal_hash"):
            blockers.append("SIGNAL_HASH_CHANGED")
        return sorted(set(blockers))

    def _guarded_payload(self, signal: dict[str, Any]) -> dict[str, Any]:
        source = signal.get("candle_source") if isinstance(signal.get("candle_source"), dict) else {}
        return {
            "symbol": str(signal.get("symbol") or "").upper(),
            "side": str(signal.get("signal") or "").upper(),
            "action": str(signal.get("signal") or "").upper(),
            "lot": 0.01,
            "entry_price": self._number(signal.get("entry"), 0),
            "stop_loss": self._number(signal.get("stop_loss"), 0),
            "take_profit": self._number(signal.get("take_profit"), 0),
            "risk_reward_ratio": self._number(signal.get("risk_reward"), 0),
            "signal_confidence": self._number(signal.get("confidence"), 0),
            "signal_hash": signal.get("signal_hash"),
            "signal_timestamp": signal.get("timestamp"),
            "setup_reason": signal.get("setup_reason") or signal.get("reason"),
            "strategy_metadata": {
                "market_structure_state": signal.get("market_structure_state") or {},
                "strategy_components": signal.get("strategy_components") or {},
                "quality_score": signal.get("quality_score") or {},
                "approval_audit": signal.get("approval_audit") or {},
                "candle_source": signal.get("candle_source") or {},
            },
            "validation_session_id": self.session["session_id"],
            "execution_mode": "AUTO_VALIDATION",
            "broker_source": source.get("broker_source") or source.get("source") or "VANTAGE_DEMO",
            "account_login": source.get("account_login"),
            "confirm": True,
            "environment": "DEMO",
            "manual_confirmation": True,
            "acknowledge_demo_only": True,
            "acknowledge_no_live_trading": True,
            "acknowledge_no_order_placement_today": True,
            "acknowledge_single_trade_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
        }

    def _load_signals(self) -> list[dict[str, Any]]:
        if self.signal_provider is None:
            return []
        payload = self.signal_provider.current(record_history=False)
        signals = payload.get("signals", [])
        return self._allowed_signals(signals if isinstance(signals, list) else [])

    def _current_signal(self, symbol: str) -> dict[str, Any] | None:
        if symbol not in self._allowed_symbols():
            return None
        if self.signal_provider is None:
            return None
        try:
            return self.signal_provider.signal_for_symbol(symbol, record_history=False)
        except TypeError:
            return self.signal_provider.signal_for_symbol(symbol)
        except Exception:
            return None

    def _account_status(self, signal: dict[str, Any]) -> dict[str, Any]:
        if self.mt5_demo_service is not None:
            try:
                return self.mt5_demo_service.get_status()
            except Exception:
                pass
        source = signal.get("candle_source") if isinstance(signal.get("candle_source"), dict) else {}
        return {
            "account_type": source.get("account_type") or "DEMO",
            "server": source.get("server") or "VantageMarkets-Demo",
            "login": source.get("account_login") or "",
        }

    def _broker_detected(self, account: dict[str, Any], signal: dict[str, Any]) -> str | None:
        source = signal.get("candle_source") if isinstance(signal.get("candle_source"), dict) else {}
        broker = str(source.get("broker_source") or source.get("source") or "").upper()
        server = str(account.get("server") or source.get("server") or "").lower()
        if "vantage" in server and account.get("account_type") == "DEMO":
            return "VANTAGE_DEMO"
        if account.get("server") and "vantage" not in server:
            return None
        if broker == "VANTAGE_DEMO":
            return "VANTAGE_DEMO"
        return broker or None

    def _tick(self, symbol: str) -> dict[str, Any]:
        service = getattr(self.guarded_execution_service, "market_data_service", None)
        if service is None:
            return {"status": "OK", "spread": 0.0}
        try:
            return service.get_symbol_tick(symbol)
        except Exception:
            return {"status": "DISCONNECTED", "spread": None}

    def _open_positions(self) -> list[dict[str, Any]]:
        if self.position_service is None:
            return []
        try:
            result = self.position_service.get_open_positions()
        except Exception:
            return []
        positions = result.get("positions", []) if isinstance(result, dict) else []
        return positions if isinstance(positions, list) else []

    def _allowed_symbols(self) -> set[str]:
        symbols = self.config.get("allowed_symbols", ["XAUUSD", "EURUSD"])
        return {str(symbol).upper() for symbol in symbols if str(symbol).upper()}

    def _allowed_signals(self, signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
        allowed = self._allowed_symbols()
        return [signal for signal in signals if str(signal.get("symbol") or "").upper() in allowed]

    def _clear_disallowed_watched_signal(self) -> None:
        if not isinstance(self._current_signal_watched, dict):
            return
        if str(self._current_signal_watched.get("symbol") or "").upper() not in self._allowed_symbols():
            self._current_signal_watched = None
            self._save_state()

    def _checked_symbol_result(self, signal: dict[str, Any]) -> dict[str, Any]:
        symbol = str(signal.get("symbol") or "").upper()
        ready = self._ready(signal)
        blockers = self._validate_signal(signal) if ready else self._readiness_blockers(signal)
        confidence = self._number(signal.get("confidence"), 0)
        return {
            "symbol": symbol,
            "status": signal.get("status_level") or signal.get("execution_status") or signal.get("signal") or "UNKNOWN",
            "confidence": signal.get("confidence"),
            "execution_status": signal.get("execution_status"),
            "risk_status": signal.get("risk_status"),
            "signal": signal.get("signal"),
            "signal_hash": signal.get("signal_hash"),
            "blocking_reason": ", ".join(blockers) if blockers else "QUALIFIED",
            "blockers": blockers,
            "ready_for_execution": ready and not blockers,
            "score": confidence,
            "what_needs_to_happen_next": signal.get("what_needs_to_happen_next"),
            "missing_requirements": signal.get("missing_requirements") if isinstance(signal.get("missing_requirements"), list) else [],
        }

    def _readiness_blockers(self, signal: dict[str, Any]) -> list[str]:
        blockers: list[str] = []
        if signal.get("execution_status") != "READY_FOR_PREVIEW":
            blockers.append("SIGNAL_NOT_READY_FOR_PREVIEW")
        if signal.get("risk_status") != "APPROVED":
            blockers.append("RISK_STATUS_NOT_APPROVED")
        if str(signal.get("signal") or "").upper() not in {"BUY", "SELL"}:
            blockers.append("NO_BUY_SELL_SIGNAL")
        missing = signal.get("missing_requirements")
        if isinstance(missing, list):
            blockers.extend(str(item.get("code") or item.get("label") or item) for item in missing if item)
        return sorted(set(blockers)) or ["NO_READY_APPROVED_SIGNAL"]

    def _best_candidate(self, checked: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not checked:
            return None
        return sorted(checked, key=lambda item: (bool(item.get("ready_for_execution")), self._number(item.get("score"), 0)), reverse=True)[0]

    def _scan_context(self, checked: list[dict[str, Any]], selected: dict[str, Any] | None) -> dict[str, Any]:
        allowed = sorted(self._allowed_symbols())
        per_symbol = {item["symbol"]: item for item in checked}
        no_qualified = "; ".join(f"{item['symbol']}: {item['blocking_reason']}" for item in checked if item.get("blocking_reason")) or "NO_ALLOWED_SYMBOL_SIGNALS"
        return {
            "watched_symbols": allowed,
            "last_checked_symbol": checked[-1]["symbol"] if checked else None,
            "best_candidate_symbol": (selected or {}).get("symbol"),
            "no_qualified_reason": no_qualified,
            "per_symbol_results": per_symbol,
            "EURUSD": per_symbol.get("EURUSD"),
            "XAUUSD": per_symbol.get("XAUUSD"),
        }

    def _refresh_session_metrics(self) -> None:
        trades = self.trades()
        closed = [trade for trade in trades if trade.get("status") == "CLOSED"]
        open_trades = [trade for trade in trades if trade.get("status") in {"OPEN", "SENT"}]
        wins = [trade for trade in closed if trade.get("result") == "WIN"]
        losses = [trade for trade in closed if trade.get("result") == "LOSS"]
        pnl_values = [self._trade_pnl(trade) for trade in closed]
        rr_values = [rr for rr in (self._trade_rr(trade) for trade in closed) if rr is not None]
        gross_profit = sum(value for value in pnl_values if value > 0)
        gross_loss = abs(sum(value for value in pnl_values if value < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0.0)
        setup_performance = self._setup_performance(closed)
        self.session.update(
            {
                "total_trades": len(trades),
                "current_closed_trades": len(closed),
                "current_open_trades": len(open_trades) + len(self._open_positions()),
                "wins": len(wins),
                "losses": len(losses),
                "win_rate": round((len(wins) / len(closed)) * 100, 2) if closed else 0.0,
                "net_pnl": round(sum(pnl_values), 2),
                "avg_rr": round(sum(rr_values) / len(rr_values), 2) if rr_values else 0.0,
                "average_rr": round(sum(rr_values) / len(rr_values), 2) if rr_values else 0.0,
                "profit_factor": round(profit_factor, 2),
                "max_drawdown": self._max_drawdown(pnl_values),
                "best_setup_type": setup_performance["best_setup_type"],
                "worst_setup_type": setup_performance["worst_setup_type"],
                "equity_curve": self._equity_curve(closed),
            }
        )
        if self.session["status"] == "RUNNING" and self.session["current_closed_trades"] >= int(self.config["target_closed_trades"]):
            self.session["status"] = "COMPLETED"
            self.session["stopped_at"] = self._timestamp()
            self.session["reason_stopped"] = "TARGET_COMPLETED"
            self.config["auto_validation_enabled"] = False
            self._log("TARGET_COMPLETED")
            self._save_state()

    def _risk_halt_reason(self) -> str | None:
        if self.session["current_closed_trades"] >= int(self.config["target_closed_trades"]):
            return "TARGET_COMPLETED"
        if self.session["net_pnl"] <= -abs(float(self.config["max_daily_loss_amount"])):
            return "MAX_DAILY_LOSS_REACHED"
        if self.session["max_drawdown"] >= abs(float(self.config["max_total_drawdown_amount"])):
            return "MAX_DRAWDOWN_REACHED"
        return None

    def _halt(self, reason: str) -> dict[str, Any]:
        self.session["status"] = "COMPLETED" if reason == "TARGET_COMPLETED" else "HALTED_RISK"
        self.session["stopped_at"] = self._timestamp()
        self.session["reason_stopped"] = reason
        self.config["auto_validation_enabled"] = False
        self._log("RISK_HALT_TRIGGERED" if reason != "TARGET_COMPLETED" else "TARGET_COMPLETED", {"reason": reason})
        self._save_state()
        return self._decision("HALTED_RISK" if reason != "TARGET_COMPLETED" else "COMPLETED", [reason])

    def _decision(self, status: str, blockers: list[str], signal: dict[str, Any] | None = None, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        decision = {
            "status": status,
            "blockers": blockers,
            "symbol": (signal or {}).get("symbol"),
            "signal_hash": (signal or {}).get("signal_hash"),
            "validation_session_id": self.session.get("session_id"),
            "guarded_sender_used": False,
            "mt5_order_sent": False,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "timestamp": self._timestamp(),
            **(extra or {}),
        }
        self._last_execution_decision = decision
        self._save_state()
        return decision

    def _daily_trade_count(self) -> int:
        today = datetime.now(timezone.utc).date()
        count = 0
        for event in self.events:
            if event.get("event") != "ORDER_SENT":
                continue
            try:
                event_date = datetime.fromisoformat(str(event.get("timestamp")).replace("Z", "+00:00")).date()
            except ValueError:
                continue
            if event_date == today:
                count += 1
        return count

    def _cooldown_active(self) -> bool:
        if self._last_trade_time is None:
            return False
        return datetime.now(timezone.utc) < self._last_trade_time + timedelta(minutes=float(self.config["cooldown_after_trade_minutes"]))

    def _next_eligible_time(self) -> str | None:
        if self._last_trade_time is None:
            return None
        return (self._last_trade_time + timedelta(minutes=float(self.config["cooldown_after_trade_minutes"]))).isoformat()

    def _ready(self, signal: dict[str, Any]) -> bool:
        return signal.get("execution_status") == "READY_FOR_PREVIEW" and signal.get("risk_status") == "APPROVED" and str(signal.get("signal") or "").upper() in {"BUY", "SELL"}

    def _halt_blocker(self, blockers: list[str]) -> bool:
        halts = {
            "LIVE_ACCOUNT_DETECTED",
            "NON_VANTAGE_BROKER_DETECTED",
            "LOT_SIZE_EXCEEDS_0_01",
            "SL_TP_REQUIRED",
            "DUPLICATE_SIGNAL_BLOCKED",
            "MAX_DAILY_TRADE_LIMIT_REACHED",
            "MAX_DRAWDOWN_REACHED",
            "MAX_DAILY_LOSS_REACHED",
            "MT5_DISCONNECT_DETECTED",
            "GUARDED_SENDER_REJECTED",
        }
        return any(item in halts for item in blockers)

    def _log(self, event: str, details: dict[str, Any] | None = None) -> None:
        self.events.append({"event": event, "details": details or {}, "timestamp": self._timestamp()})
        self._save_state()

    def log_runner_error(self, message: str) -> None:
        self._log("RUNNER_ERROR", {"error": message})

    def update_runner_state(self, **updates: Any) -> None:
        self.runner_state.update(updates)

    def should_auto_start_runner(self) -> bool:
        return self.session.get("status") == "RUNNING" and self.config.get("auto_validation_enabled") is True

    def watched_signal_is_watchlist(self) -> bool:
        watched = self._current_signal_watched if isinstance(self._current_signal_watched, dict) else {}
        quality = watched.get("quality_score") if isinstance(watched.get("quality_score"), dict) else {}
        return str(watched.get("status_level") or quality.get("rating") or "").upper() == "WATCHLIST"

    def _empty_runner_state(self) -> dict[str, Any]:
        return {
            "runner_active": False,
            "runner_last_tick_at": None,
            "runner_next_tick_at": None,
            "runner_interval_seconds": 3,
            "run_once_in_progress": False,
            "last_run_once_duration_ms": None,
            "last_runner_error": "",
        }

    def _empty_session(self) -> dict[str, Any]:
        return {
            "session_id": "",
            "started_at": None,
            "stopped_at": None,
            "status": "IDLE",
            "target_closed_trades": 30,
            "current_closed_trades": 0,
            "current_open_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "net_pnl": 0.0,
            "avg_rr": 0.0,
            "average_rr": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0,
            "best_setup_type": "Unavailable",
            "worst_setup_type": "Unavailable",
            "equity_curve": [],
            "reason_stopped": "",
        }

    def _load_state(self) -> None:
        try:
            if not self.state_path.exists():
                return
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if isinstance(data.get("config"), dict):
            self.config = {**self._default_config(), **data["config"]}
            self.config["live_execution_enabled"] = False
            self.config["broker_execution_enabled"] = False
        if isinstance(data.get("session"), dict):
            self.session = {**self._empty_session(), **data["session"]}
        if isinstance(data.get("events"), list):
            self.events = [event for event in data["events"] if isinstance(event, dict)][-500:]
        if isinstance(data.get("last_execution_decision"), dict):
            self._last_execution_decision = data["last_execution_decision"]
        if isinstance(data.get("current_signal_watched"), dict):
            self._current_signal_watched = data["current_signal_watched"]
        if self.session.get("status") == "RUNNING":
            self.config["auto_validation_enabled"] = True

    def _save_state(self) -> None:
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "config": self.config,
                "session": self.session,
                "events": self.events[-500:],
                "last_execution_decision": self._last_execution_decision,
                "current_signal_watched": self._current_signal_watched,
                "updated_at": self._timestamp(),
            }
            self.state_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        except OSError:
            pass

    def _default_config(self) -> dict[str, Any]:
        return {
            "auto_validation_enabled": False,
            "target_closed_trades": 30,
            "allowed_symbols": ["XAUUSD", "EURUSD"],
            "broker_required": "VANTAGE_DEMO",
            "account_type_required": "DEMO",
            "lot_size": 0.01,
            "max_open_trades_total": 1,
            "max_open_trades_per_symbol": 1,
            "max_daily_trades": 30,
            "max_daily_loss_amount": 100.0,
            "max_total_drawdown_amount": 150.0,
            "min_confidence": 75,
            "min_rr": 1.5,
            "require_sl_tp": True,
            "cooldown_after_trade_minutes": 15,
            "stop_after_target_reached": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def _safe_config(self, payload: dict[str, Any]) -> dict[str, Any]:
        safe = dict(self.config)
        for key in [
            "target_closed_trades",
            "max_daily_loss_amount",
            "max_total_drawdown_amount",
            "cooldown_after_trade_minutes",
            "max_daily_trades",
        ]:
            if key in payload:
                safe[key] = payload[key]
        safe["auto_validation_enabled"] = bool(payload.get("auto_validation_enabled", safe["auto_validation_enabled"]))
        safe["allowed_symbols"] = [symbol for symbol in payload.get("allowed_symbols", safe["allowed_symbols"]) if symbol in {"XAUUSD", "EURUSD", "NIFTY50"}] or ["XAUUSD", "EURUSD"]
        safe["lot_size"] = min(float(payload.get("lot_size", 0.01)), 0.01)
        safe["broker_required"] = "VANTAGE_DEMO"
        safe["account_type_required"] = "DEMO"
        safe["live_execution_enabled"] = False
        safe["broker_execution_enabled"] = False
        return safe

    def _max_drawdown(self, pnl_values: list[float]) -> float:
        peak = 0.0
        equity = 0.0
        max_drawdown = 0.0
        for value in pnl_values:
            equity += value
            peak = max(peak, equity)
            max_drawdown = max(max_drawdown, peak - equity)
        return round(max_drawdown, 2)

    def _trade_pnl(self, trade: dict[str, Any]) -> float:
        for key in ["net_pnl", "profit_loss", "realized_pnl", "total_pnl"]:
            if key in trade:
                return self._number(trade.get(key), 0)
        return 0.0

    def _trade_rr(self, trade: dict[str, Any]) -> float | None:
        for key in ["risk_reward_ratio", "risk_reward", "rr"]:
            if key in trade:
                value = self._number(trade.get(key), 0)
                return value if value > 0 else None
        return None

    def _setup_type(self, trade: dict[str, Any]) -> str:
        direct = str(trade.get("setup_type") or "").strip()
        if direct:
            return direct
        metadata = trade.get("strategy_metadata") if isinstance(trade.get("strategy_metadata"), dict) else {}
        metadata_setup = str(metadata.get("setup_type") or "").strip()
        if metadata_setup:
            return metadata_setup
        components = metadata.get("strategy_components") if isinstance(metadata.get("strategy_components"), dict) else {}
        ordered = [
            ("liquidity_sweep", "Sweep"),
            ("bos", "BOS"),
            ("choch", "CHOCH"),
            ("fvg", "FVG"),
            ("order_block", "OB"),
        ]
        active = [label for key, label in ordered if bool(components.get(key))]
        return " + ".join(active) if active else "Unknown Setup"

    def _setup_performance(self, closed: list[dict[str, Any]]) -> dict[str, str]:
        grouped: dict[str, list[float]] = {}
        for trade in closed:
            grouped.setdefault(self._setup_type(trade), []).append(self._trade_pnl(trade))
        if not grouped:
            return {"best_setup_type": "Unavailable", "worst_setup_type": "Unavailable"}
        ranked = sorted(
            grouped.items(),
            key=lambda item: (sum(item[1]) / len(item[1]), sum(item[1]), len(item[1])),
        )
        return {"best_setup_type": ranked[-1][0], "worst_setup_type": ranked[0][0]}

    def _equity_curve(self, closed: list[dict[str, Any]]) -> list[dict[str, Any]]:
        def sort_key(trade: dict[str, Any]) -> str:
            return str(trade.get("closed_at") or trade.get("updated_at") or trade.get("created_at") or trade.get("timestamp") or "")

        equity = 0.0
        peak = 0.0
        points: list[dict[str, Any]] = []
        for index, trade in enumerate(sorted(closed, key=sort_key), start=1):
            pnl = self._trade_pnl(trade)
            equity += pnl
            peak = max(peak, equity)
            points.append(
                {
                    "trade_index": index,
                    "trade_id": trade.get("trade_id") or trade.get("id") or f"trade-{index}",
                    "timestamp": trade.get("closed_at") or trade.get("updated_at") or trade.get("created_at") or trade.get("timestamp"),
                    "pnl": round(pnl, 2),
                    "equity": round(equity, 2),
                    "drawdown": round(peak - equity, 2),
                }
            )
        return points

    def _number(self, value: Any, fallback: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return fallback

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()
