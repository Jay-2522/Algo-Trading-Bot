from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REASON_STORE_PATH = PROJECT_ROOT / "data" / "reason_panel" / "reason_messages.json"


class ExecutionReasonPanelService:
    """Persist factual execution decisions into the Reason Panel store."""

    def __init__(self, store_path: Path | None = None) -> None:
        self.store_path = store_path or DEFAULT_REASON_STORE_PATH

    def latest_for_session(self, session_id: str, limit: int = 3) -> list[dict[str, Any]]:
        """Return stable, current-session messages without mutating the reason store."""
        meaningful = {"SCAN_RESULT", "OPEN_CONFIRMED", "POSITION_MONITOR", "CLOSED", "CLOSED_WIN", "CLOSED_LOSS", "ACCEPTED"}
        records = [
            item
            for item in self._read()
            if self._text(item.get("validation_session_id") or item.get("active_session_id")) == self._text(session_id)
            and self._text(item.get("status")).upper() in meaningful
            and not self._is_legacy_scan_message(item)
        ]
        records.sort(
            key=lambda item: (self._timestamp_value(self._text(item.get("timestamp"))), self._text(item.get("event_id") or item.get("id"))),
            reverse=True,
        )
        seen: set[str] = set()
        result: list[dict[str, Any]] = []
        for item in records:
            event_id = self._text(item.get("event_id") or item.get("id"))
            if not event_id or event_id in seen:
                continue
            seen.add(event_id)
            result.append(item)
            if len(result) >= max(1, limit):
                break
        return result

    def _is_legacy_scan_message(self, item: dict[str, Any]) -> bool:
        if self._text(item.get("status")).upper() != "SCAN_RESULT":
            return False
        if isinstance(item.get("canonical_scan"), dict):
            return False
        reason = self._text(item.get("reason") or item.get("final_decision_reason"))
        return bool(reason) and any(
            marker in reason.lower()
            for marker in [
                "score 2/2",
                "h4 history",
                "m15 history",
                "bos",
                "fvg",
                "outside london",
                "confidence threshold",
                "threshold 75",
                "watchlist",
                "required round 3 rule failed",
            ]
        )

    def persist_order_sent(
        self,
        *,
        signal: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
        result: dict[str, Any] | None = None,
        decision: dict[str, Any] | None = None,
        timestamp: str | None = None,
    ) -> dict[str, Any] | None:
        signal = signal or {}
        payload = payload or {}
        result = result or {}
        decision = decision or {}
        ticket = self._text(result.get("ticket") or result.get("mt5_ticket") or decision.get("ticket") or payload.get("ticket"))
        if not ticket or ticket == "0":
            return None
        message = self._accepted_message(signal=signal, payload=payload, result=result, decision=decision, timestamp=timestamp)
        self._upsert(message)
        return message

    def persist_backfill_position(
        self,
        position: dict[str, Any],
        *,
        signal_hash: str = "",
        timestamp: str = "",
        data_source: str = "MT5_DEMO",
    ) -> dict[str, Any] | None:
        ticket = self._text(position.get("ticket"))
        symbol = self._text(position.get("symbol")).upper()
        side = self._text(position.get("side") or position.get("type")).upper()
        if not ticket or not symbol:
            return None
        message = {
            "id": self._id(ticket, signal_hash),
            "event_id": self._id(ticket, signal_hash),
            "groqGenerated": False,
            "reason": f"{symbol} was accepted and opened as a {side or 'trade'} trade because the guarded demo validation passed, risk status was approved, and MT5 executed the order successfully. Ticket: {ticket}.",
            "source": "execution",
            "status": "Accepted",
            "symbol": symbol,
            "side": side,
            "ticket": ticket,
            "signal_hash": signal_hash,
            "strategy_profile": "DEMO_COLLECTION",
            "decision": "READY_FOR_GUARDED_DEMO_TEST",
            "risk_status": "APPROVED",
            "execution_status": "READY_FOR_PREVIEW",
            "order_opened": True,
            "mt5_retcode": self._text(position.get("mt5_retcode") or position.get("retcode") or "10009"),
            "mt5_comment": self._text(position.get("mt5_comment") or position.get("comment") or "Request executed"),
            "timestamp": timestamp or self._timestamp(),
            "data_source": data_source,
        }
        self._upsert(message)
        return message

    def persist_open_confirmed(
        self,
        position: dict[str, Any],
        *,
        adaptive_level: int | str | None = None,
        session_id: str = "",
        timestamp: str = "",
    ) -> dict[str, Any] | None:
        ticket = self._text(position.get("ticket") or position.get("mt5_ticket"))
        symbol = self._text(position.get("symbol")).upper()
        side = self._text(position.get("side") or position.get("type") or position.get("action")).upper()
        if not ticket or not symbol:
            return None
        message_id = f"execution-open-confirmed-{ticket}"
        for existing in self._read():
            if self._text(existing.get("id")) == message_id:
                existing_reason = self._text(existing.get("reason"))
                if self._text(existing.get("status")).upper() == "OPEN_CONFIRMED" and existing_reason.upper().startswith("OPEN_CONFIRMED") and "\n" in existing_reason:
                    return existing
                break
        entry = position.get("entry_price") or position.get("price_open")
        current_price = position.get("current_price") or position.get("price_current")
        sl = position.get("stop_loss") or position.get("sl")
        tp = position.get("take_profit") or position.get("tp")
        floating_pnl = position.get("floating_pnl") if position.get("floating_pnl") is not None else position.get("profit")
        message = {
            "id": message_id,
            "event_id": message_id,
            "groqGenerated": False,
            "reason": "\n".join(
                [
                    "OPEN_CONFIRMED",
                    f"Symbol: {symbol}",
                    f"Direction: {side or 'TRADE'}",
                    f"Ticket: {ticket}",
                    f"Entry: {self._text(entry) or 'Unavailable'}",
                    f"Current price: {self._text(current_price) or 'Unavailable'}",
                    f"SL: {self._text(sl) or 'Unavailable'}",
                    f"TP: {self._text(tp) or 'Unavailable'}",
                    f"Floating P&L: {self._text(floating_pnl) or '0'}",
                    f"Adaptive level: {self._text(adaptive_level) or '0'}",
                ]
            ),
            "source": "execution",
            "status": "OPEN_CONFIRMED",
            "symbol": symbol,
            "side": side,
            "ticket": ticket,
            "strategy_profile": "DEMO_COLLECTION",
            "decision": "OPEN_CONFIRMED",
            "order_opened": True,
            "entry": entry,
            "current_price": current_price,
            "sl": sl,
            "tp": tp,
            "floating_pnl": floating_pnl,
            "adaptive_level": adaptive_level,
            "validation_session_id": session_id,
            "final_decision_reason": "OPEN_CONFIRMED",
            "timestamp": timestamp or self._timestamp(),
            "data_source": "MT5_LIVE_POSITION_SYNC",
        }
        self._upsert(message)
        return message

    def persist_closed_confirmed(
        self,
        trade: dict[str, Any],
        *,
        session_id: str = "",
        timestamp: str = "",
    ) -> dict[str, Any] | None:
        ticket = self._text(trade.get("mt5_ticket") or trade.get("ticket"))
        symbol = self._text(trade.get("symbol")).upper()
        side = self._text(trade.get("side") or trade.get("direction") or trade.get("action")).upper()
        if not ticket or not symbol:
            return None
        pnl = trade.get("net_pnl") if trade.get("net_pnl") is not None else trade.get("total_pnl") if trade.get("total_pnl") is not None else trade.get("profit_loss") if trade.get("profit_loss") is not None else trade.get("pnl")
        result = self._text(trade.get("result")).upper() or ("WIN" if self._number(pnl) > 0 else "LOSS" if self._number(pnl) < 0 else "BREAKEVEN")
        status = "CLOSED_WIN" if result == "WIN" else "CLOSED_LOSS" if result == "LOSS" else "CLOSED"
        duration = self._text(trade.get("duration_minutes"))
        exit_reason = self._text(trade.get("exit_reason")) or "MT5 history confirmed close"
        metadata = trade.get("strategy_metadata") if isinstance(trade.get("strategy_metadata"), dict) else {}
        round3 = metadata.get("round3_diagnostics") if isinstance(metadata.get("round3_diagnostics"), dict) else {}
        autopsy = trade.get("autopsy") if isinstance(trade.get("autopsy"), dict) else {}
        missing = round3.get("confirmation_missing") if isinstance(round3.get("confirmation_missing"), list) else []
        if not missing and isinstance(autopsy.get("confirmations_missing"), list):
            missing = autopsy.get("confirmations_missing", [])
        weak = self._join_text([self._text(item).lower() for item in missing[:2]]) if missing else "one or more entry conditions weakened"
        if status == "CLOSED_LOSS":
            autopsy_reason = self._text(autopsy.get("reason_for_loss"))
            fix = self._text(autopsy.get("suggested_rule_fix"))
            score_text = self._text(round3.get("confirmation_score") or autopsy.get("score_at_entry")) or "n/a"
            fallback_reason = f"Entry was based on score {score_text}, but {weak}; price reached {exit_reason.lower()} with P&L {self._text(pnl) or '0'}."
            reason = f"{side or 'Trade'} failed{f' after {duration} minutes' if duration else ''}. {autopsy_reason or fallback_reason}{f' Suggested fix: {fix}' if fix else ''}"
        elif status == "CLOSED_WIN":
            reason = f"{side or 'Trade'} reached target{f' after {duration} minutes' if duration else ''}. Momentum carried price to take profit with P&L {self._text(pnl) or '0'}."
        else:
            reason = f"{side or 'Trade'} closed{f' after {duration} minutes' if duration else ''}. Exit reason: {exit_reason}. P&L {self._text(pnl) or '0'}."
        message_id = f"execution-{status.lower()}-{ticket}"
        message = {
            "id": message_id,
            "event_id": message_id,
            "groqGenerated": False,
            "reason": reason,
            "source": "execution",
            "status": status,
            "symbol": symbol,
            "side": side,
            "ticket": ticket,
            "strategy_profile": self._text(trade.get("strategy_profile")) or "DEMO_COLLECTION",
            "decision": status,
            "order_closed": True,
            "pnl": pnl,
            "exit_reason": self._text(trade.get("exit_reason")),
            "autopsy": autopsy,
            "validation_session_id": session_id or self._text(trade.get("validation_session_id")),
            "final_decision_reason": status,
            "timestamp": timestamp or self._text(trade.get("closed_at") or trade.get("close_time") or trade.get("generated_at")) or self._timestamp(),
            "data_source": "MT5_HISTORY_CLOSE_SYNC",
        }
        self._upsert(message)
        return message

    def persist_scan_result(self, scan: dict[str, Any], *, session_id: str = "") -> dict[str, Any] | None:
        symbol = self._text(scan.get("symbol")).upper()
        if not symbol:
            return None
        timestamp = self._text(scan.get("timestamp")) or self._timestamp()
        event_id = self._text(scan.get("event_id")) or f"scan-result-{symbol.lower()}-{timestamp}"
        reason = self._text(scan.get("reason")) or self._scan_reason(scan)
        message = {
            "id": event_id,
            "event_id": event_id,
            "groqGenerated": False,
            "reason": reason,
            "source": "execution",
            "status": "SCAN_RESULT",
            "symbol": symbol,
            "side": self._text(scan.get("direction") or scan.get("direction_candidate")).upper(),
            "ticket": "",
            "strategy_profile": "DEMO_COLLECTION",
            "decision": self._text(scan.get("decision") or scan.get("execution_decision")),
            "order_opened": False,
            "adaptive_level": scan.get("adaptive_level"),
            "confirmation_score": scan.get("confirmations_passed"),
            "confirmation_required": scan.get("required_confirmations"),
            "canonical_scan": scan,
            "base_passed": scan.get("base_passed"),
            "base_total": scan.get("base_total"),
            "confirmations_passed": scan.get("confirmations_passed"),
            "confirmations_total": scan.get("confirmations_total"),
            "required_confirmations": scan.get("required_confirmations"),
            "missing_base_gates": scan.get("missing_base_gates") if isinstance(scan.get("missing_base_gates"), list) else [],
            "missing_confirmations": scan.get("missing_confirmations") if isinstance(scan.get("missing_confirmations"), list) else [],
            "order_allowed": scan.get("order_allowed"),
            "order_block_reason": scan.get("order_block_reason"),
            "htf_bias": scan.get("htf_bias"),
            "momentum": scan.get("momentum"),
            "pullback_retest": scan.get("pullback_retest"),
            "bos": scan.get("bos"),
            "liquidity_sweep": scan.get("liquidity_sweep"),
            "fvg": scan.get("fvg"),
            "fvg_retest": scan.get("fvg_retest"),
            "session_bonus": scan.get("session_bonus"),
            "conditions": scan.get("conditions") if isinstance(scan.get("conditions"), dict) else {},
            "validation_session_id": session_id,
            "final_decision_reason": reason,
            "timestamp": timestamp,
            "data_source": "ROUND_SCAN_TRACE",
        }
        self._upsert(message)
        return message

    def persist_risk_halt(self, diagnostics: dict[str, Any], *, session_id: str = "") -> dict[str, Any]:
        reason = self._text(diagnostics.get("reason")) or "RISK_HALT"
        status = self._text(diagnostics.get("status")) or "RISK_HALTED"
        message_text = self._text(diagnostics.get("message")) or f"Risk halted: {reason.replace('_', ' ').lower()}."
        event_id = f"risk-halt-{session_id or 'active'}-{reason.lower()}"
        if status == "RISK_CLEARED":
            event_id = f"risk-halt-cleared-{session_id or 'active'}-{reason.lower()}"
        message = {
            "id": event_id,
            "event_id": event_id,
            "groqGenerated": False,
            "reason": message_text,
            "source": "execution",
            "status": status,
            "symbol": self._text(diagnostics.get("symbol")).upper() or "ROUND_3",
            "side": "",
            "ticket": "",
            "strategy_profile": "DEMO_COLLECTION",
            "decision": status,
            "order_opened": False,
            "validation_session_id": session_id,
            "active_session_id": session_id,
            "risk_halt_reason": reason,
            "risk_halt_active": diagnostics.get("active"),
            "risk_halt_stale": diagnostics.get("stale"),
            "net_pnl": diagnostics.get("net_pnl"),
            "max_daily_loss_amount": diagnostics.get("max_daily_loss_amount"),
            "max_drawdown": diagnostics.get("max_drawdown"),
            "max_total_drawdown_amount": diagnostics.get("max_total_drawdown_amount"),
            "mt5_health_status": diagnostics.get("mt5_health_status"),
            "timestamp": self._text(diagnostics.get("timestamp")) or self._timestamp(),
            "data_source": "ROUND_RISK_HALT",
        }
        self._upsert(message)
        return message

    def persist_adaptive_level_change(self, change: dict[str, Any], *, session_id: str = "") -> dict[str, Any] | None:
        symbol = self._text(change.get("symbol")).upper()
        if not symbol:
            return None
        old_level = self._text(change.get("old_level") if change.get("old_level") is not None else change.get("from_level")) or "0"
        new_level = self._text(change.get("new_level") if change.get("new_level") is not None else change.get("to_level")) or old_level
        timestamp = self._text(change.get("timestamp")) or self._timestamp()
        raw_reason = self._text(change.get("reason")) or "adaptive level updated"
        friendly_reason = raw_reason.replace("_", " ").strip().rstrip(".")
        if old_level == new_level:
            reason = f"{symbol} stayed at Level {new_level} because {friendly_reason}."
            event_id = f"adaptive-level-stayed-{symbol.lower()}-{new_level}-{friendly_reason.lower().replace(' ', '-')}"
        else:
            reason = f"{symbol} moved to Level {new_level} because {friendly_reason}."
            event_id = f"adaptive-level-change-{symbol.lower()}-{old_level}-{new_level}-{timestamp}"
        message = {
            "id": event_id,
            "event_id": event_id,
            "groqGenerated": False,
            "reason": reason,
            "source": "execution",
            "status": "ADAPTIVE_LEVEL_CHANGE",
            "symbol": symbol,
            "side": "",
            "ticket": "",
            "strategy_profile": "DEMO_COLLECTION",
            "decision": "ADAPTIVE_LEVEL_CHANGE",
            "order_opened": False,
            "adaptive_level": new_level,
            "old_adaptive_level": old_level,
            "validation_session_id": session_id,
            "active_session_id": session_id,
            "final_decision_reason": reason,
            "timestamp": timestamp,
            "data_source": "SYMBOL_ADAPTIVE_STATE",
        }
        self._upsert(message)
        return message

    def persist_resume_failed(self, diagnostics: dict[str, Any], *, session_id: str = "") -> dict[str, Any]:
        reason_text = self._text(diagnostics.get("block_reason")) or "resume was blocked"
        timestamp = self._text(diagnostics.get("timestamp")) or self._timestamp()
        event_id = f"resume-failed-{session_id or 'active'}-{timestamp}"
        message_text = f"Resume failed because {reason_text}."
        message = {
            "id": event_id,
            "event_id": event_id,
            "groqGenerated": False,
            "reason": message_text,
            "source": "execution",
            "status": "RESUME_FAILED",
            "symbol": "ROUND_3",
            "side": "",
            "ticket": "",
            "strategy_profile": "DEMO_COLLECTION",
            "decision": "RESUME_FAILED",
            "order_opened": False,
            "validation_session_id": session_id,
            "active_session_id": session_id,
            "resume_allowed": diagnostics.get("can_resume"),
            "validation_status": diagnostics.get("validation_status"),
            "mt5_status": diagnostics.get("mt5_status"),
            "risk_status": diagnostics.get("risk_status"),
            "final_decision_reason": message_text,
            "timestamp": timestamp,
            "data_source": "AUTO_VALIDATION_RESUME_CHECK",
        }
        self._upsert(message)
        return message

    def persist_exit_management(self, diagnostic: dict[str, Any], *, session_id: str = "") -> dict[str, Any] | None:
        ticket = self._text(diagnostic.get("ticket"))
        symbol = self._text(diagnostic.get("symbol")).upper()
        if not ticket or not symbol:
            return None
        status = self._text(diagnostic.get("exit_status")).upper() or "EXIT_MANAGEMENT"
        action = self._text(diagnostic.get("exit_action")).upper() or "HOLD"
        reason = self._text(diagnostic.get("exit_reason")).replace("_", " ").lower()
        r_multiple = self._text(diagnostic.get("current_r_multiple"))
        if action == "MODIFY_SL":
            text = f"Ticket {ticket} moved SL to {self._text(diagnostic.get('new_stop_loss')) or 'a protected level'} because {reason} triggered at {r_multiple}R."
        elif action == "CLOSE":
            text = f"Ticket {ticket} close was requested because {reason} triggered at {r_multiple}R."
        else:
            text = self._text(diagnostic.get("why_still_holding")) or f"Ticket {ticket} is still held because no exit trigger has fired."
        event_id = f"exit-management-{ticket}-{status.lower()}-{action.lower()}"
        message = {
            "id": event_id,
            "event_id": event_id,
            "groqGenerated": False,
            "reason": text,
            "source": "execution",
            "status": "POSITION_MONITOR",
            "symbol": symbol,
            "side": self._text(diagnostic.get("direction")).upper(),
            "ticket": ticket,
            "strategy_profile": "DEMO_COLLECTION",
            "decision": status,
            "order_opened": False,
            "validation_session_id": session_id,
            "active_session_id": session_id,
            "current_r_multiple": diagnostic.get("current_r_multiple"),
            "floating_pnl": diagnostic.get("floating_pnl"),
            "exit_action": action,
            "exit_reason": diagnostic.get("exit_reason"),
            "next_exit_trigger": diagnostic.get("next_exit_trigger"),
            "final_decision_reason": text,
            "timestamp": self._text(diagnostic.get("timestamp")) or self._timestamp(),
            "data_source": "EXIT_MANAGEMENT_LOOP",
        }
        self._upsert(message)
        return message

    def _accepted_message(
        self,
        *,
        signal: dict[str, Any],
        payload: dict[str, Any],
        result: dict[str, Any],
        decision: dict[str, Any],
        timestamp: str | None,
    ) -> dict[str, Any]:
        ticket = self._text(result.get("ticket") or result.get("mt5_ticket") or decision.get("ticket") or payload.get("ticket"))
        symbol = self._text(payload.get("symbol") or signal.get("symbol") or decision.get("symbol")).upper()
        side = self._text(payload.get("action") or payload.get("side") or signal.get("signal") or result.get("side")).upper()
        signal_hash = self._text(payload.get("signal_hash") or signal.get("signal_hash") or decision.get("signal_hash"))
        strategy_profile = self._text(payload.get("strategy_profile") or signal.get("strategy_profile") or decision.get("strategy_profile") or "DEMO_COLLECTION")
        retcode = self._text(result.get("retcode") or result.get("final_retcode") or decision.get("mt5_retcode"))
        comment = self._text(result.get("comment") or result.get("final_comment") or decision.get("mt5_comment"))
        strategy_metadata = payload.get("strategy_metadata") if isinstance(payload.get("strategy_metadata"), dict) else {}
        round3 = strategy_metadata.get("round3_diagnostics") if isinstance(strategy_metadata.get("round3_diagnostics"), dict) else {}
        entry = result.get("entry") or result.get("entry_estimate") or payload.get("entry_price") or signal.get("entry")
        sl = result.get("sl") or payload.get("stop_loss") or signal.get("stop_loss")
        tp = result.get("tp") or payload.get("take_profit") or signal.get("take_profit")
        score = self._text(round3.get("confirmation_score") or decision.get("confirmation_score") or payload.get("confirmation_score")) or "0"
        required = self._text(round3.get("confirmation_required") or decision.get("confirmation_required") or payload.get("confirmation_required")) or "5"
        direction = "bearish" if side == "SELL" else "bullish" if side == "BUY" else "directional"
        level = self._text(round3.get("adaptive_level") or round3.get("current_strategy_level")) or "0"
        passed = {self._text(item).upper() for item in round3.get("confirmation_passed", [])} if isinstance(round3.get("confirmation_passed"), list) else set()
        drivers = []
        if "H4/H1 TREND ALIGNMENT" in passed or self._text(round3.get("trend_alignment_status")).upper() == "ALIGNED":
            drivers.append(f"{direction} HTF trend")
        if any("MOMENTUM" in item for item in passed):
            drivers.append("momentum")
        if any("BOS" in item for item in passed):
            drivers.append("BOS")
        if any("LIQUIDITY" in item for item in passed):
            drivers.append("liquidity sweep")
        if any("FVG" in item for item in passed):
            drivers.append("FVG retest")
        if any("PULLBACK" in item or "RETEST" in item for item in passed):
            drivers.append("pullback/retest")
        if not drivers:
            drivers.append(f"{direction} setup conditions")
        final_reason = f"{side or 'Trade'} executed because {self._join_text(drivers)} aligned. Adaptive Level {level} accepted score {score}."
        data_source = self._text(payload.get("data_source") or signal.get("data_source") or strategy_metadata.get("data_source"))
        return {
            "id": self._id(ticket, signal_hash),
            "event_id": self._id(ticket, signal_hash),
            "groqGenerated": False,
            "reason": final_reason,
            "source": "execution",
            "status": "Accepted",
            "symbol": symbol,
            "side": side,
            "ticket": ticket,
            "signal_hash": signal_hash,
            "strategy_profile": strategy_profile or "DEMO_COLLECTION",
            "decision": "READY_FOR_GUARDED_DEMO_TEST",
            "risk_status": "APPROVED",
            "execution_status": "READY_FOR_PREVIEW",
            "order_opened": True,
            "mt5_retcode": retcode,
            "mt5_comment": comment,
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "confirmation_score": score,
            "confirmation_required": required,
            "rule_name": self._text(round3.get("rule_name")),
            "passed_rules": round3.get("passed_rules") if isinstance(round3.get("passed_rules"), list) else [],
            "failed_rules": round3.get("failed_rules") if isinstance(round3.get("failed_rules"), list) else [],
            "advisory_warnings": round3.get("advisory_warnings") if isinstance(round3.get("advisory_warnings"), list) else [],
            "session": self._text(round3.get("session")),
            "RR": round3.get("RR"),
            "bos_status": self._text(round3.get("bos_status")),
            "fvg_status": self._text(round3.get("fvg_status")),
            "h4_history_status": self._text(round3.get("h4_history_status")),
            "m15_history_status": self._text(round3.get("m15_history_status")),
            "final_decision_reason": final_reason,
            "timestamp": timestamp or self._timestamp(),
            "data_source": data_source,
        }

    def _upsert(self, message: dict[str, Any]) -> None:
        messages = self._read()
        ticket = self._text(message.get("ticket"))
        signal_hash = self._text(message.get("signal_hash"))
        message_id = self._text(message.get("id"))
        status = self._text(message.get("status"))
        filtered = []
        for item in messages:
            if message_id and self._text(item.get("id")) == message_id:
                continue
            if ticket and self._text(item.get("ticket")) == ticket and status and self._text(item.get("status")) == status:
                continue
            if signal_hash and self._text(item.get("signal_hash")) == signal_hash and self._text(item.get("source")) == "execution":
                continue
            filtered.append(item)
        next_messages = [message, *filtered]
        next_messages.sort(key=lambda item: self._timestamp_value(self._text(item.get("timestamp"))), reverse=True)
        self._write(next_messages[:50])

    def _read(self) -> list[dict[str, Any]]:
        try:
            parsed = json.loads(self.store_path.read_text(encoding="utf-8"))
            return [item for item in parsed if isinstance(item, dict)] if isinstance(parsed, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def _write(self, messages: list[dict[str, Any]]) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.store_path.write_text(json.dumps(messages, indent=2), encoding="utf-8")

    def _id(self, ticket: str, signal_hash: str = "") -> str:
        return f"execution-order-sent-{ticket or signal_hash}"

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _timestamp_value(self, value: str) -> float:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return 0.0

    def _text(self, value: Any) -> str:
        return "" if value is None else str(value).strip()

    def _number(self, value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _join_text(self, values: list[str]) -> str:
        values = [value for value in values if value]
        if len(values) <= 1:
            return values[0] if values else "setup conditions"
        if len(values) == 2:
            return f"{values[0]} and {values[1]}"
        return f"{', '.join(values[:-1])}, and {values[-1]}"

    def _scan_reason(self, scan: dict[str, Any]) -> str:
        symbol = self._text(scan.get("symbol")).upper() or "Signal"
        if isinstance(scan.get("base_gates"), list) and isinstance(scan.get("confirmations"), list):
            base_passed = int(self._number(scan.get("base_passed")))
            base_total = int(self._number(scan.get("base_total"))) or len(scan.get("base_gates") or [])
            confirmations_passed = int(self._number(scan.get("confirmations_passed")))
            confirmations_total = int(self._number(scan.get("confirmations_total"))) or len(scan.get("confirmations") or [])
            required = int(self._number(scan.get("required_confirmations")))
            level = self._text(scan.get("adaptive_level")) or "0"
            missing_base = [self._text(item) for item in scan.get("missing_base_gates", []) if self._text(item)] if isinstance(scan.get("missing_base_gates"), list) else []
            missing_confirmations = [self._text(item) for item in scan.get("missing_confirmations", []) if self._text(item)] if isinstance(scan.get("missing_confirmations"), list) else []
            if scan.get("order_allowed") is True:
                return f"{symbol} is ready. Base gates {base_passed}/{base_total} and confirmations {confirmations_passed}/{confirmations_total} meet Level {level} rules."
            if missing_base:
                return f"{symbol} is blocked because {missing_base[0].lower()} is not passing. Base gates {base_passed}/{base_total}, confirmations {confirmations_passed}/{confirmations_total}."
            if confirmations_passed < required:
                needs = self._join_text(missing_confirmations[:2]) if missing_confirmations else "one more confirmation"
                return f"{symbol} is blocked with confirmations {confirmations_passed}/{confirmations_total}. Level {level} needs {required}; missing {needs}."
            reason = self._text(scan.get("order_block_reason")) or "the current safety checks have not approved the trade"
            return f"{symbol} is blocked because {reason[0].lower() + reason[1:] if reason else reason}"

        direction = self._text(scan.get("direction") or scan.get("direction_candidate")).upper()
        bias = "bearish" if direction == "SELL" else "bullish" if direction == "BUY" else "unclear"
        score = self._text(scan.get("score") or 0)
        required = self._text(scan.get("required_score") or 0)
        conditions = scan.get("conditions") if isinstance(scan.get("conditions"), dict) else {}
        failed = {self._text(item).upper() for item in scan.get("failed_hard_gates", [])} if isinstance(scan.get("failed_hard_gates"), list) else set()
        level = self._text(scan.get("adaptive_level")) or "0"
        if level == "3" and ({"LEVEL_3_FAST_TRIGGER_MISSING", "LEVEL_3_NEEDS_ONE_FAST_TRIGGER"} & failed):
            return f"{symbol} is close. It has trend bias, clean spread, and RR, but still needs one trigger such as momentum, BOS, liquidity sweep, or pullback."
        missing = []
        if conditions.get("bos") is False:
            missing.append("BOS missing")
        if conditions.get("liquidity_sweep") is False:
            missing.append("liquidity sweep absent")
        if conditions.get("momentum") is False:
            missing.append("momentum absent")
        if conditions.get("pullback_retest") is False and conditions.get("momentum") is False:
            missing.append("pullback/retest absent")
        if conditions.get("fvg_retest") is False and conditions.get("bos") is False and conditions.get("liquidity_sweep") is False:
            missing.append("no structure confirmation")
        decision = self._text(scan.get("decision") or scan.get("execution_decision")).replace("_", " ").lower() or "evaluated"
        suffix = f" {self._join_text(missing)}." if missing else " Confirmations aligned."
        return f"{symbol} {bias} bias detected. Score {score}/{required}.{suffix} Trade {decision}."
