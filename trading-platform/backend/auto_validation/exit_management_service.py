from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class AutoValidationExitManagementService:
    """Production-shaped exit manager, restricted to guarded demo execution."""

    def __init__(
        self,
        signal_provider: Any | None = None,
        market_data_service: Any | None = None,
        guarded_sender_service: Any | None = None,
        journal_service: Any | None = None,
    ) -> None:
        self.signal_provider = signal_provider
        self.market_data_service = market_data_service
        self.guarded_sender_service = guarded_sender_service
        self.journal_service = journal_service
        self._latest = self._empty_summary("NOT_RUN", "Exit management has not run yet.")
        self._history: list[dict[str, Any]] = []
        self._active_close_tickets: set[str] = set()
        self._close_attempts: dict[str, int] = {}
        self._last_close_attempt_at: dict[str, str] = {}

    def status(self) -> dict[str, Any]:
        return self._latest

    def history(self, limit: int = 100) -> list[dict[str, Any]]:
        return self._history[-limit:]

    def run(
        self,
        *,
        session: dict[str, Any],
        config: dict[str, Any],
        positions: list[dict[str, Any]],
        trades: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not self._enabled(session, config):
            self._latest = self._empty_summary("DISABLED", "Exit management is only enabled for active DEMO_COLLECTION sessions.")
            self._history.append(self._latest)
            return self._latest

        trades_by_ticket = {str(trade.get("mt5_ticket") or ""): trade for trade in trades if str(trade.get("mt5_ticket") or "")}
        managed: list[dict[str, Any]] = []
        actions: list[dict[str, Any]] = []
        blocked: list[dict[str, Any]] = []
        failed: list[dict[str, Any]] = []

        for position in positions:
            trade = trades_by_ticket.get(self._ticket(position), {})
            decision = self._decision(position, trade, config)
            safety_blockers = self._exit_safety_blockers(decision, position, trade, session, config)
            if safety_blockers and decision["action"] != "HOLD":
                decision["action"] = "HOLD"
                decision["exit_reason"] = "EXIT_SAFETY_BLOCKED"
                decision["safety_blockers"] = safety_blockers
                blocked.append(decision)
            managed.append(decision)
            if decision["action"] == "HOLD":
                continue
            if decision["action"] == "CLOSE" and decision["ticket"] in self._active_close_tickets:
                decision["execution_result"] = self._blocked("DUPLICATE_CLOSE_ATTEMPT_IN_PROGRESS")
                blocked.append(decision)
                continue
            result = self._execute(decision, position, trade, session, config)
            decision["execution_result"] = result
            if result.get("status") in {"SLTP_MODIFIED", "POSITION_CLOSED", "POSITION_PARTIALLY_CLOSED"}:
                actions.append(decision)
                self._record_exit_update(position, trade, decision, result)
            elif result.get("status") == "BLOCKED":
                blocked.append(decision)
            else:
                failed.append(decision)

        self._latest = {
            "status": "READY",
            "message": "Exit management evaluated current AUTO validation positions.",
            "enabled": True,
            "profile": str(config.get("strategy_profile") or ""),
            "positions_checked": len(positions),
            "actions_taken": len(actions),
            "blocked_actions": len(blocked),
            "failed_actions": len(failed),
            "break_even_moves": len([item for item in actions if item.get("exit_reason") == "BREAK_EVEN_PROTECTION"]),
            "trailing_stop_moves": len([item for item in actions if item.get("exit_reason") == "TRAILING_STOP"]),
            "time_stale_exits": len([item for item in actions if item.get("exit_reason") == "TIME_STALE_EXIT"]),
            "signal_reversal_exits": len([item for item in actions if item.get("exit_reason") == "SIGNAL_REVERSAL_EXIT"]),
            "confidence_drop_exits": len([item for item in actions if item.get("exit_reason") == "CONFIDENCE_DROP_EXIT"]),
            "soft_adverse_exits": len([item for item in actions if item.get("exit_reason") == "SOFT_ADVERSE_EXIT"]),
            "no_progress_exits": len([item for item in actions if item.get("exit_reason") == "NO_PROGRESS_EXIT"]),
            "managed_positions": managed,
            "exit_outcomes": self._exit_outcomes(trades),
            "last_action": actions[-1] if actions else None,
            "last_failed_action": failed[-1] if failed else None,
            "timestamp": self._timestamp(),
            **self._safety_flags(),
        }
        self._history.append(self._latest)
        return self._latest

    def _enabled(self, session: dict[str, Any], config: dict[str, Any]) -> bool:
        return (
            session.get("status") == "RUNNING"
            and str(config.get("strategy_profile") or "").upper() == "DEMO_COLLECTION"
            and config.get("exit_management_enabled", True) is True
            and config.get("live_execution_enabled") is False
            and config.get("broker_execution_enabled") is False
        )

    def _decision(self, position: dict[str, Any], trade: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        symbol = str(position.get("symbol") or trade.get("symbol") or "").upper()
        side = self._side(position, trade)
        entry = self._number(position.get("entry_price") or position.get("price_open") or trade.get("entry_price"), 0.0)
        current = self._current_price(symbol, side, position)
        stop_loss = self._number(position.get("stop_loss") or position.get("sl") or trade.get("stop_loss"), 0.0)
        take_profit = self._number(position.get("take_profit") or position.get("tp") or trade.get("take_profit"), 0.0)
        volume = self._number(position.get("lot") or position.get("volume") or trade.get("lot"), 0.0)
        unrealized_pnl = self._number(position.get("floating_pnl") or position.get("profit") or trade.get("profit_loss"), 0.0)
        risk = abs(entry - stop_loss) if entry > 0 and stop_loss > 0 else 0.0
        profit_distance = (current - entry) if side == "BUY" else (entry - current)
        r_multiple = round(profit_distance / risk, 3) if risk > 0 else 0.0
        signal = self._current_signal(symbol)
        signal_available = isinstance(signal, dict)
        signal_side = str(signal.get("signal") or "").upper() if signal else ""
        signal_confidence = self._number(signal.get("confidence") if signal else None, 0.0)
        signal_execution_status = str(signal.get("execution_status") or signal.get("status_level") or "").upper() if signal else ""
        signal_risk_status = str(signal.get("risk_status") or "").upper() if signal else ""
        entry_confidence = self._number(trade.get("signal_confidence"), signal_confidence)
        age_minutes = self._age_minutes(position, trade)
        stale_minutes = int(config.get("exit_stale_minutes", 45))
        confidence_floor = float(config.get("exit_confidence_floor", 40))
        confidence_drop = float(config.get("exit_confidence_drop_points", 25))
        soft_adverse_minutes = float(config.get("exit_soft_adverse_minutes", 20))
        no_progress_minutes = float(config.get("exit_no_progress_minutes", 30))
        no_progress_min_r = float(config.get("exit_no_progress_min_r", 0.3))
        symbol_settings = self._symbol_exit_settings(symbol, config)
        if symbol_settings:
            stale_minutes = int(symbol_settings.get("stale_exit_minutes", stale_minutes))
            confidence_floor = float(symbol_settings.get("confidence_floor", confidence_floor))
            confidence_drop = float(symbol_settings.get("confidence_drop_points", confidence_drop))
            soft_adverse_minutes = float(symbol_settings.get("soft_adverse_minutes", soft_adverse_minutes))
            no_progress_minutes = float(symbol_settings.get("no_progress_minutes", no_progress_minutes))
            no_progress_min_r = float(symbol_settings.get("no_progress_min_r", no_progress_min_r))
        confidence_dropped = bool(signal_confidence and (signal_confidence <= confidence_floor or entry_confidence - signal_confidence >= confidence_drop))
        signal_no_longer_valid = bool(
            signal_available
            and (
                signal_side in {"WAIT", "REJECTED", "NO_SIGNAL"}
                or (signal_execution_status and signal_execution_status not in {"READY_FOR_PREVIEW", "READY", "TRADEABLE"})
                or (signal_risk_status and signal_risk_status != "APPROVED")
            )
        )

        base = {
            "ticket": self._ticket(position),
            "symbol": symbol,
            "side": side,
            "entry_price": entry,
            "current_price": current,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "volume": volume,
            "unrealized_pnl": unrealized_pnl,
            "distance_to_sl": round(abs(current - stop_loss), 6) if current > 0 and stop_loss > 0 else None,
            "distance_to_tp": round(abs(take_profit - current), 6) if current > 0 and take_profit > 0 else None,
            "r_multiple": r_multiple,
            "age_minutes": age_minutes,
            "signal_side": signal_side,
            "signal_confidence": signal_confidence,
            "signal_execution_status": signal_execution_status,
            "signal_risk_status": signal_risk_status,
            "entry_confidence": entry_confidence,
            "strategy_profile": str(config.get("strategy_profile") or ""),
            "action": "HOLD",
            "exit_reason": "HOLD_BELOW_BREAKEVEN_TRIGGER",
            "hold_reason": "HOLD_BELOW_BREAKEVEN_TRIGGER",
            "hold_checks": {
                "break_even": "HOLD_BELOW_BREAKEVEN_TRIGGER",
                "trailing": "HOLD_BELOW_TRAILING_TRIGGER",
                "stale": "HOLD_WAITING_FOR_STALE_TIMEOUT",
                "reversal": "HOLD_NO_REVERSAL",
                "confidence": "HOLD_NO_CONFIDENCE_DROP",
                "soft_adverse": "HOLD_NO_SOFT_ADVERSE_EXIT",
                "no_progress": "HOLD_NO_PROGRESS_EXIT_NOT_DUE",
            },
            "new_stop_loss": None,
            "close_volume": 0.0,
            "timestamp": self._timestamp(),
        }
        if not symbol or side not in {"BUY", "SELL"} or entry <= 0 or current <= 0 or volume <= 0:
            return {**base, "action": "HOLD", "exit_reason": "INSUFFICIENT_POSITION_DATA"}

        if signal_side in {"BUY", "SELL"} and signal_side != side:
            return {**base, "action": "CLOSE", "exit_reason": "SIGNAL_REVERSAL_EXIT", "close_volume": volume}
        if age_minutes > soft_adverse_minutes and unrealized_pnl < 0 and (confidence_dropped or signal_no_longer_valid):
            return {**base, "action": "CLOSE", "exit_reason": "SOFT_ADVERSE_EXIT", "close_volume": volume}
        if confidence_dropped:
            return {**base, "action": "CLOSE", "exit_reason": "CONFIDENCE_DROP_EXIT", "close_volume": volume}
        if age_minutes >= stale_minutes and r_multiple < float(config.get("exit_stale_min_r", 0.2)):
            return {**base, "action": "CLOSE", "exit_reason": "TIME_STALE_EXIT", "close_volume": volume}

        if risk <= 0:
            return {**base, "exit_reason": "HOLD_WAITING_FOR_VALID_RISK"}
        if age_minutes > no_progress_minutes and r_multiple < no_progress_min_r:
            return {**base, "action": "CLOSE", "exit_reason": "NO_PROGRESS_EXIT", "close_volume": volume}
        break_even_r = float(symbol_settings.get("break_even_trigger_r", config.get("break_even_trigger_r", 1.0)) if symbol_settings else config.get("break_even_trigger_r", 1.0))
        trailing_r = float(symbol_settings.get("trailing_stop_trigger_r", config.get("trailing_stop_trigger_r", 1.5)) if symbol_settings else config.get("trailing_stop_trigger_r", 1.5))
        trailing_distance_r = float(symbol_settings.get("trailing_stop_distance_r", config.get("trailing_stop_distance_r", 0.75)) if symbol_settings else config.get("trailing_stop_distance_r", 0.75))

        if r_multiple >= trailing_r:
            new_sl = current - (risk * trailing_distance_r) if side == "BUY" else current + (risk * trailing_distance_r)
            if self._stop_improves(side, stop_loss, new_sl, entry):
                return {**base, "action": "MODIFY_SL", "exit_reason": "TRAILING_STOP", "new_stop_loss": self._round_price(symbol, new_sl)}
        if r_multiple >= break_even_r and self._stop_worse_than_entry(side, stop_loss, entry):
            return {**base, "action": "MODIFY_SL", "exit_reason": "BREAK_EVEN_PROTECTION", "new_stop_loss": self._round_price(symbol, entry)}
        return {**base, "exit_reason": self._hold_reason(age_minutes, stale_minutes, r_multiple, break_even_r, signal_side, confidence_dropped)}

    def _hold_reason(self, age_minutes: float, stale_minutes: float, r_multiple: float, break_even_r: float, signal_side: str, confidence_dropped: bool) -> str:
        if r_multiple < break_even_r:
            return "HOLD_BELOW_BREAKEVEN_TRIGGER"
        if age_minutes < stale_minutes:
            return "HOLD_WAITING_FOR_STALE_TIMEOUT"
        if signal_side not in {"BUY", "SELL"}:
            return "HOLD_NO_REVERSAL"
        if not confidence_dropped:
            return "HOLD_NO_CONFIDENCE_DROP"
        return "HOLD_NO_EXIT_TRIGGER"

    def _execute(self, decision: dict[str, Any], position: dict[str, Any], trade: dict[str, Any], session: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        if self.guarded_sender_service is None:
            return self._blocked("GUARDED_SENDER_UNAVAILABLE")
        payload = {
            "environment": "DEMO",
            "symbol": decision["symbol"],
            "ticket": decision["ticket"],
            "position_ticket": decision["ticket"],
            "side": decision["side"],
            "action": decision["side"],
            "lot": min(float(decision["volume"] or 0.0), 0.01),
            "volume": min(float(decision["volume"] or 0.0), 0.01),
            "close_volume": min(float(decision.get("close_volume") or decision["volume"] or 0.0), 0.01),
            "stop_loss": decision.get("new_stop_loss") or decision.get("stop_loss"),
            "take_profit": decision.get("take_profit"),
            "exit_reason": decision["exit_reason"],
            "strategy_profile": "DEMO_COLLECTION",
            "validation_session_id": session.get("session_id"),
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "confirm": True,
        }
        if decision["action"] == "MODIFY_SL":
            method = getattr(self.guarded_sender_service, "modify_demo_position_stop", None)
        else:
            method = getattr(self.guarded_sender_service, "close_demo_position", None)
        if not callable(method):
            return self._blocked("GUARDED_EXIT_METHOD_UNAVAILABLE")
        try:
            if decision["action"] == "CLOSE":
                self._active_close_tickets.add(str(decision["ticket"]))
                self._close_attempts[str(decision["ticket"])] = self._close_attempts.get(str(decision["ticket"]), 0) + 1
                self._last_close_attempt_at[str(decision["ticket"])] = self._timestamp()
            result = method(payload)
        except Exception as exc:
            return {"status": "EXIT_FAILED", "reason": str(exc), **self._safety_flags(), "timestamp": self._timestamp()}
        finally:
            if decision["action"] == "CLOSE" and str(decision["ticket"]) in self._active_close_tickets:
                self._active_close_tickets.remove(str(decision["ticket"]))
        return result if isinstance(result, dict) else self._blocked("INVALID_GUARDED_EXIT_RESULT")

    def _exit_safety_blockers(self, decision: dict[str, Any], position: dict[str, Any], trade: dict[str, Any], session: dict[str, Any], config: dict[str, Any]) -> list[str]:
        blockers: list[str] = []
        symbol = str(decision.get("symbol") or "").upper()
        settings = self._symbol_exit_settings(symbol, config)
        tick = self._market_tick(symbol)
        spread = self._number(tick.get("spread"), None)
        max_spread = settings.get("max_spread") if settings else None
        max_spread = float(max_spread if max_spread is not None else (1.0 if symbol == "XAUUSD" else 0.0003))
        if tick.get("status") not in {"OK", "TICK_AVAILABLE_DIRECT", "MARKET_READY"}:
            blockers.append("VALID_TICK_REQUIRED")
        if spread is None or spread > max_spread:
            blockers.append("SPREAD_CHECK_FAILED")
        if not self._tick_fresh(tick, int(settings.get("max_tick_age_seconds", 10) if settings else 10)):
            blockers.append("TICK_FRESHNESS_CHECK_FAILED")
        if not self._position_owned(position, trade, session):
            blockers.append("POSITION_OWNERSHIP_NOT_CONFIRMED")
        if self._close_attempts.get(str(decision.get("ticket")), 0) >= int(config.get("exit_max_close_retries", 3)) and decision.get("action") == "CLOSE":
            blockers.append("MAX_CLOSE_RETRIES_REACHED")
        if config.get("live_execution_enabled") is True or config.get("broker_execution_enabled") is True:
            blockers.append("LIVE_OR_BROKER_EXECUTION_ENABLED")
        decision["market_safety"] = {"tick_status": tick.get("status"), "spread": spread, "max_spread": max_spread, "tick_timestamp": tick.get("timestamp")}
        return blockers

    def _market_tick(self, symbol: str) -> dict[str, Any]:
        if self.market_data_service is None:
            return {"status": "SYMBOL_TICK_UNAVAILABLE", "spread": None}
        try:
            tick = self.market_data_service.get_symbol_tick(symbol)
        except Exception:
            return {"status": "SYMBOL_TICK_UNAVAILABLE", "spread": None}
        return tick if isinstance(tick, dict) else {"status": "SYMBOL_TICK_UNAVAILABLE", "spread": None}

    def _tick_fresh(self, tick: dict[str, Any], max_age_seconds: int) -> bool:
        timestamp = tick.get("timestamp") or tick.get("time")
        parsed = self._parse_time(timestamp)
        if parsed is None:
            return tick.get("status") in {"OK", "TICK_AVAILABLE_DIRECT", "MARKET_READY"}
        return (datetime.now(timezone.utc) - parsed).total_seconds() <= max_age_seconds

    def _position_owned(self, position: dict[str, Any], trade: dict[str, Any], session: dict[str, Any]) -> bool:
        session_id = str(session.get("session_id") or "")
        if session_id and str(trade.get("validation_session_id") or "") == session_id:
            return True
        if session_id and str(position.get("validation_session_id") or "") == session_id:
            return True
        comment = str(position.get("comment") or "").upper()
        return bool(session_id and ("AUTO" in comment or "VALIDATION" in comment) and self._parse_time(position.get("time") or position.get("opened_at")) is not None)

    def _symbol_exit_settings(self, symbol: str, config: dict[str, Any]) -> dict[str, Any]:
        settings = config.get("per_symbol_exit_settings")
        if not isinstance(settings, dict):
            return {}
        item = settings.get(symbol)
        return item if isinstance(item, dict) else {}

    def _exit_outcomes(self, trades: list[dict[str, Any]]) -> dict[str, Any]:
        managed = [trade for trade in trades if isinstance(trade.get("exit_management"), dict)]
        by_reason: dict[str, int] = {}
        for trade in managed:
            reason = str((trade.get("exit_management") or {}).get("last_exit_reason") or trade.get("exit_reason") or "UNKNOWN")
            by_reason[reason] = by_reason.get(reason, 0) + 1
        return {
            "managed_trades": len(managed),
            "exit_reasons": by_reason,
            "data_source": "exit_management_metadata",
            "separate_from_entry_outcomes": True,
        }

    def _record_exit_update(self, position: dict[str, Any], trade: dict[str, Any], decision: dict[str, Any], result: dict[str, Any]) -> None:
        if self.journal_service is None or not hasattr(self.journal_service, "record_exit_management_update"):
            return
        try:
            self.journal_service.record_exit_management_update(
                self._ticket(position),
                {
                    "exit_management": {
                        "last_exit_reason": decision.get("exit_reason"),
                        "last_exit_action": decision.get("action"),
                        "last_exit_result": result.get("status"),
                        "new_stop_loss": decision.get("new_stop_loss"),
                        "r_multiple": decision.get("r_multiple"),
                        "updated_at": self._timestamp(),
                    },
                    "exit_reason": decision.get("exit_reason") if decision.get("action") == "CLOSE" else trade.get("exit_reason"),
                    "notes": f"{trade.get('notes', '')} Exit management: {decision.get('exit_reason')} -> {result.get('status')}.".strip(),
                },
            )
        except Exception:
            return

    def _current_signal(self, symbol: str) -> dict[str, Any] | None:
        if self.signal_provider is None:
            return None
        try:
            signal = self.signal_provider.signal_for_symbol(symbol, record_history=False, strategy_profile="DEMO_COLLECTION")
        except TypeError:
            try:
                signal = self.signal_provider.signal_for_symbol(symbol, record_history=False)
            except TypeError:
                signal = self.signal_provider.signal_for_symbol(symbol)
        except Exception:
            return None
        return signal if isinstance(signal, dict) else None

    def _current_price(self, symbol: str, side: str, position: dict[str, Any]) -> float:
        direct = self._number(position.get("current_price") or position.get("price_current"), 0.0)
        if direct > 0:
            return direct
        tick = {}
        if self.market_data_service is not None:
            try:
                tick = self.market_data_service.get_symbol_tick(symbol)
            except Exception:
                tick = {}
        if side == "BUY":
            return self._number(tick.get("bid"), 0.0)
        return self._number(tick.get("ask"), 0.0)

    def _age_minutes(self, position: dict[str, Any], trade: dict[str, Any]) -> float:
        opened = position.get("opened_at") or trade.get("opened_at") or trade.get("created_at") or position.get("time")
        parsed = self._parse_time(opened)
        if parsed is None:
            return 0.0
        return max(0.0, round((datetime.now(timezone.utc) - parsed).total_seconds() / 60, 2))

    def _parse_time(self, value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if isinstance(value, (int, float)) and value > 0:
            return datetime.fromtimestamp(float(value), timezone.utc)
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

    def _stop_worse_than_entry(self, side: str, stop_loss: float, entry: float) -> bool:
        return stop_loss <= 0 or (side == "BUY" and stop_loss < entry) or (side == "SELL" and stop_loss > entry)

    def _stop_improves(self, side: str, stop_loss: float, new_stop: float, entry: float) -> bool:
        if side == "BUY":
            return new_stop > max(stop_loss, entry)
        return new_stop < min(stop_loss if stop_loss > 0 else entry, entry)

    def _side(self, position: dict[str, Any], trade: dict[str, Any]) -> str:
        raw = str(position.get("side") or position.get("type") or trade.get("side") or "").upper()
        if raw in {"BUY", "0"}:
            return "BUY"
        if raw in {"SELL", "1"}:
            return "SELL"
        return raw

    def _ticket(self, position: dict[str, Any]) -> str:
        return str(position.get("ticket") or position.get("mt5_ticket") or "")

    def _round_price(self, symbol: str, value: float) -> float:
        return round(value, 2 if symbol == "XAUUSD" else 5)

    def _number(self, value: Any, fallback: float) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return fallback
        return number if number == number else fallback

    def _blocked(self, reason: str) -> dict[str, Any]:
        return {"status": "BLOCKED", "reason": reason, "failed_guard": reason, **self._safety_flags(), "timestamp": self._timestamp()}

    def _empty_summary(self, status: str, message: str) -> dict[str, Any]:
        return {
            "status": status,
            "message": message,
            "enabled": False,
            "positions_checked": 0,
            "actions_taken": 0,
            "blocked_actions": 0,
            "failed_actions": 0,
            "managed_positions": [],
            "last_action": None,
            "last_failed_action": None,
            "timestamp": self._timestamp(),
            **self._safety_flags(),
        }

    def _safety_flags(self) -> dict[str, bool]:
        return {
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
        }

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()
