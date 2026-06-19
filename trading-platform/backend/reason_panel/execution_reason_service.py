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
        message_id = f"execution-{status.lower()}-{ticket}"
        message = {
            "id": message_id,
            "event_id": message_id,
            "groqGenerated": False,
            "reason": "\n".join(
                [
                    status,
                    f"Symbol: {symbol}",
                    f"Direction: {side or 'TRADE'}",
                    f"Ticket: {ticket}",
                    f"P&L: {self._text(pnl) or '0'}",
                    f"Exit reason: {self._text(trade.get('exit_reason')) or 'MT5 history confirmed close'}",
                    f"Closed time: {self._text(trade.get('closed_at') or trade.get('close_time')) or 'Unavailable'}",
                ]
            ),
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
            "validation_session_id": session_id or self._text(trade.get("validation_session_id")),
            "final_decision_reason": status,
            "timestamp": timestamp or self._text(trade.get("closed_at") or trade.get("close_time") or trade.get("generated_at")) or self._timestamp(),
            "data_source": "MT5_HISTORY_CLOSE_SYNC",
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
        required = self._text(round3.get("confirmation_required") or decision.get("confirmation_required") or payload.get("confirmation_required")) or "2"
        final_reason = "\n".join(
            [
                f"{symbol} {side or 'TRADE'} opened.",
                f"Ticket: {ticket}",
                f"Entry: {self._text(entry) or 'Unavailable'}",
                f"SL: {self._text(sl) or 'Unavailable'}",
                f"TP: {self._text(tp) or 'Unavailable'}",
                f"Score: {score}/{required}",
            ]
        )
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
