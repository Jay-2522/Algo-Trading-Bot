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
        data_source = self._text(payload.get("data_source") or signal.get("data_source") or strategy_metadata.get("data_source"))
        return {
            "id": self._id(ticket, signal_hash),
            "groqGenerated": False,
            "reason": f"{symbol} was accepted and opened as a {side or 'trade'} trade because the guarded demo validation passed, risk status was approved, and MT5 executed the order successfully. Ticket: {ticket}.",
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
            "timestamp": timestamp or self._timestamp(),
            "data_source": data_source,
        }

    def _upsert(self, message: dict[str, Any]) -> None:
        messages = self._read()
        ticket = self._text(message.get("ticket"))
        signal_hash = self._text(message.get("signal_hash"))
        message_id = self._text(message.get("id"))
        filtered = []
        for item in messages:
            if message_id and self._text(item.get("id")) == message_id:
                continue
            if ticket and self._text(item.get("ticket")) == ticket:
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
