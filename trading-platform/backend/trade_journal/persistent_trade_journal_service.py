from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_JOURNAL_PATH = PROJECT_ROOT / "data" / "trade_journal" / "trade_journal.json"

TRADE_SOURCES = {"MT5_DEMO", "SIMULATION", "FUTURE_BROKER"}
TRADE_STATUSES = {"PLANNED", "SENT", "OPEN", "CLOSED", "REJECTED", "CANCELLED"}
TRADE_RESULTS = {"WIN", "LOSS", "BREAKEVEN", "OPEN", "REJECTED", "UNKNOWN"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class PersistentTradeJournalService:
    """File-backed trade journal for explicit demo/simulation lifecycle records."""

    def __init__(self, journal_path: Path | None = None) -> None:
        self.journal_path = journal_path or DEFAULT_JOURNAL_PATH

    def get_status(self) -> dict[str, Any]:
        trades = self.list_trades(limit=100000)
        return {
            "status": "OPERATIONAL",
            "storage": "JSON_FILE",
            "path": str(self.journal_path),
            "record_count": len(trades),
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def create_planned_trade(self, payload: dict[str, Any]) -> dict[str, Any]:
        trade = self._base_record(payload, status="PLANNED", result="UNKNOWN")
        return self._upsert_trade(trade)

    def record_order_sent(self, payload: dict[str, Any]) -> dict[str, Any]:
        trade = self._base_record(payload, status="SENT", result="OPEN")
        trade["mt5_ticket"] = self._text(payload.get("mt5_ticket") or payload.get("ticket"))
        trade["mt5_retcode"] = self._text(payload.get("mt5_retcode") or payload.get("retcode"))
        trade["mt5_comment"] = self._text(payload.get("mt5_comment") or payload.get("comment"))
        return self._upsert_trade(trade)

    def record_order_rejected(self, payload: dict[str, Any]) -> dict[str, Any]:
        trade = self._base_record(payload, status="REJECTED", result="REJECTED")
        trade["mt5_ticket"] = self._text(payload.get("mt5_ticket") or payload.get("ticket"))
        trade["mt5_retcode"] = self._text(payload.get("mt5_retcode") or payload.get("retcode"))
        trade["mt5_comment"] = self._text(payload.get("mt5_comment") or payload.get("comment"))
        return self._upsert_trade(trade)

    def record_trade_opened(self, payload: dict[str, Any]) -> dict[str, Any]:
        trade = self._base_record(payload, status="OPEN", result="OPEN")
        trade["opened_at"] = self._text(payload.get("opened_at")) or utc_now_iso()
        trade["mt5_ticket"] = self._text(payload.get("mt5_ticket") or payload.get("ticket"))
        return self._upsert_trade(trade)

    def record_open_position(self, payload: dict[str, Any]) -> dict[str, Any]:
        ticket = self._text(payload.get("mt5_ticket") or payload.get("ticket"))
        existing = self._find_by_mt5_ticket(ticket) if ticket else None
        payload = {**payload, "trade_id": existing.get("trade_id") if existing else (payload.get("trade_id") or f"mt5_demo_{ticket}")}
        trade = self._base_record(payload, status="OPEN", result="OPEN")
        trade["opened_at"] = self._text(payload.get("opened_at")) or utc_now_iso()
        trade["mt5_ticket"] = ticket
        trade["mt5_retcode"] = self._text(payload.get("mt5_retcode") or payload.get("retcode"))
        trade["mt5_comment"] = self._text(payload.get("mt5_comment") or payload.get("comment"))
        trade["profit_loss"] = self._number_or_none(payload.get("profit_loss")) or 0.0
        trade["account_login"] = self._text(payload.get("account_login"))
        trade["server"] = self._text(payload.get("server"))
        return self._upsert_trade(trade)

    def record_trade_closed(self, payload: dict[str, Any]) -> dict[str, Any]:
        ticket = self._text(payload.get("mt5_ticket") or payload.get("ticket"))
        existing = self._find_by_mt5_ticket(ticket) if ticket and not payload.get("trade_id") else None
        if existing:
            payload = {**existing, **payload, "trade_id": existing["trade_id"]}
        trade = self._base_record(payload, status="CLOSED", result=self._closed_result(payload))
        trade["opened_at"] = self._text(payload.get("opened_at"))
        trade["closed_at"] = self._text(payload.get("closed_at") or payload.get("close_time")) or utc_now_iso()
        trade["close_price"] = self._number_or_none(payload.get("close_price"))
        trade["profit_loss"] = self._number_or_none(payload.get("profit_loss"))
        trade["realized_pnl"] = self._number_or_none(payload.get("realized_pnl"))
        trade["swap"] = self._number_or_none(payload.get("swap")) or 0.0
        trade["commission"] = self._number_or_none(payload.get("commission")) or 0.0
        trade["total_pnl"] = self._number_or_none(payload.get("total_pnl") or payload.get("net_pnl") or payload.get("profit_loss"))
        trade["net_pnl"] = self._number_or_none(payload.get("net_pnl") or payload.get("total_pnl") or payload.get("profit_loss"))
        trade["duration_minutes"] = self._number_or_none(payload.get("duration_minutes"))
        trade["exit_reason"] = self._text(payload.get("exit_reason") or "UNKNOWN")
        trade["mt5_ticket"] = ticket
        trade["mt5_retcode"] = self._text(payload.get("mt5_retcode") or payload.get("retcode"))
        trade["mt5_comment"] = self._text(payload.get("mt5_comment") or payload.get("comment"))
        trade["account_login"] = self._text(payload.get("account_login"))
        trade["server"] = self._text(payload.get("server"))
        return self._upsert_trade(trade)

    def mark_trade_closed_by_ticket(self, ticket: str | int, close_payload: dict[str, Any]) -> dict[str, Any] | None:
        existing = self.get_trade_by_ticket(ticket)
        if existing is None:
            return None
        return self.record_trade_closed({**existing, **close_payload, "trade_id": existing["trade_id"], "mt5_ticket": existing.get("mt5_ticket")})

    def get_open_trades(self) -> list[dict[str, Any]]:
        return [trade for trade in self.list_trades(limit=100000) if trade.get("status") == "OPEN"]

    def get_closed_trades(self) -> list[dict[str, Any]]:
        return [trade for trade in self.list_trades(limit=100000) if trade.get("status") == "CLOSED"]

    def get_trade_by_ticket(self, ticket: str | int) -> dict[str, Any] | None:
        return self._find_by_mt5_ticket(self._text(ticket))

    def calculate_realized_summary(self) -> dict[str, Any]:
        trades = self.list_trades(limit=100000)
        closed = [trade for trade in trades if trade.get("status") == "CLOSED"]
        wins = [trade for trade in closed if trade.get("result") == "WIN"]
        losses = [trade for trade in closed if trade.get("result") == "LOSS"]
        breakeven = [trade for trade in closed if trade.get("result") == "BREAKEVEN"]
        pnl_values = [float(trade.get("net_pnl") if trade.get("net_pnl") is not None else trade.get("profit_loss") or 0) for trade in closed]
        win_values = [value for value in pnl_values if value > 0]
        loss_values = [value for value in pnl_values if value < 0]
        durations = [float(trade.get("duration_minutes") or 0) for trade in closed if trade.get("duration_minutes") is not None]
        return {
            "status": "READY",
            "total_trades": len(trades),
            "open_demo_trades": len([trade for trade in trades if trade.get("status") == "OPEN"]),
            "closed_demo_trades": len(closed),
            "wins": len(wins),
            "losses": len(losses),
            "breakeven": len(breakeven),
            "win_rate": round((len(wins) / len(closed)) * 100, 2) if closed else 0.0,
            "net_pnl": round(sum(pnl_values), 2) if pnl_values else 0.0,
            "gross_profit": round(sum(win_values), 2) if win_values else 0.0,
            "gross_loss": round(sum(loss_values), 2) if loss_values else 0.0,
            "avg_win": round(sum(win_values) / len(win_values), 2) if win_values else 0.0,
            "avg_loss": round(sum(loss_values) / len(loss_values), 2) if loss_values else 0.0,
            "avg_duration_minutes": round(sum(durations) / len(durations), 2) if durations else 0.0,
            "empty_state": len(closed) == 0,
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def get_trade(self, trade_id: str) -> dict[str, Any] | None:
        return next((trade for trade in self.list_trades(limit=100000) if trade["trade_id"] == trade_id), None)

    def list_trades(self, limit: int = 100) -> list[dict[str, Any]]:
        records = self._read_store().get("trades", [])
        sorted_records = sorted(records, key=lambda item: item.get("created_at", ""), reverse=True)
        return sorted_records[: max(1, limit)]

    def get_recent_trades(self, limit: int = 20) -> list[dict[str, Any]]:
        return self.list_trades(limit=limit)

    def get_summary(self) -> dict[str, Any]:
        trades = self.list_trades(limit=100000)
        closed = [trade for trade in trades if trade.get("status") == "CLOSED"]
        wins = [trade for trade in closed if trade.get("result") == "WIN"]
        pnl_values = [float(trade.get("profit_loss") or 0) for trade in closed]
        rr_values = [float(trade.get("risk_reward_ratio") or 0) for trade in trades if trade.get("risk_reward_ratio") is not None]
        by_status = {status: len([trade for trade in trades if trade.get("status") == status]) for status in sorted(TRADE_STATUSES)}
        realized = self.calculate_realized_summary()
        return {
            "status": "READY",
            "total_trades": len(trades),
            "planned_trades": by_status.get("PLANNED", 0),
            "sent_demo_orders": by_status.get("SENT", 0),
            "open_demo_trades": by_status.get("OPEN", 0),
            "closed_demo_trades": by_status.get("CLOSED", 0),
            "rejected_trades": by_status.get("REJECTED", 0),
            "wins": realized["wins"],
            "losses": realized["losses"],
            "breakeven": realized["breakeven"],
            "win_rate": realized["win_rate"],
            "net_pnl": realized["net_pnl"],
            "gross_profit": realized["gross_profit"],
            "gross_loss": realized["gross_loss"],
            "avg_win": realized["avg_win"],
            "avg_loss": realized["avg_loss"],
            "avg_duration_minutes": realized["avg_duration_minutes"],
            "avg_rr": round(sum(rr_values) / len(rr_values), 2) if rr_values else 0.0,
            "by_status": by_status,
            "empty_state": len(trades) == 0,
            "message": "No completed demo trades yet." if not closed else "Trade journal summary derived from recorded trades.",
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def clear_test_data_only(self) -> dict[str, Any]:
        self._write_store({"trades": []})
        return {"status": "CLEARED_TEST_DATA_ONLY", "record_count": 0}

    def _base_record(self, payload: dict[str, Any], status: str, result: str) -> dict[str, Any]:
        now = utc_now_iso()
        existing = self.get_trade(str(payload.get("trade_id"))) if payload.get("trade_id") else None
        created_at = existing.get("created_at") if existing else now
        return {
            "trade_id": self._text(payload.get("trade_id")) or f"trade_{uuid4().hex[:12]}",
            "source": self._enum(payload.get("source"), TRADE_SOURCES, "SIMULATION"),
            "environment": "DEMO",
            "symbol": self._text(payload.get("symbol")).upper(),
            "side": self._text(payload.get("side") or payload.get("action")).upper(),
            "lot": self._number_or_none(payload.get("lot")),
            "entry_price": self._number_or_none(payload.get("entry_price")),
            "stop_loss": self._number_or_none(payload.get("stop_loss")),
            "take_profit": self._number_or_none(payload.get("take_profit")),
            "risk_reward_ratio": self._number_or_none(payload.get("risk_reward_ratio") or payload.get("rr")),
            "status": self._enum(status, TRADE_STATUSES, "PLANNED"),
            "mt5_ticket": self._text(payload.get("mt5_ticket")),
            "mt5_retcode": self._text(payload.get("mt5_retcode")),
            "mt5_comment": self._text(payload.get("mt5_comment")),
            "account_login": self._text(payload.get("account_login")),
            "server": self._text(payload.get("server")),
            "broker_source": self._text(payload.get("broker_source")) or (existing or {}).get("broker_source", ""),
            "validation_session_id": self._text(payload.get("validation_session_id")) or (existing or {}).get("validation_session_id", ""),
            "execution_mode": self._text(payload.get("execution_mode")) or (existing or {}).get("execution_mode", ""),
            "signal_confidence": self._number_or_none(payload.get("signal_confidence")) if payload.get("signal_confidence") is not None else (existing or {}).get("signal_confidence"),
            "signal_hash": self._text(payload.get("signal_hash")) or (existing or {}).get("signal_hash", ""),
            "setup_reason": self._text(payload.get("setup_reason")) or (existing or {}).get("setup_reason", ""),
            "strategy_metadata": payload.get("strategy_metadata") if isinstance(payload.get("strategy_metadata"), dict) else (existing or {}).get("strategy_metadata", {}),
            "opened_at": self._text(payload.get("opened_at")),
            "closed_at": self._text(payload.get("closed_at")),
            "close_price": self._number_or_none(payload.get("close_price")),
            "profit_loss": self._number_or_none(payload.get("profit_loss")),
            "realized_pnl": self._number_or_none(payload.get("realized_pnl")),
            "swap": self._number_or_none(payload.get("swap")),
            "commission": self._number_or_none(payload.get("commission")),
            "total_pnl": self._number_or_none(payload.get("total_pnl")),
            "net_pnl": self._number_or_none(payload.get("net_pnl")),
            "duration_minutes": self._number_or_none(payload.get("duration_minutes")),
            "exit_reason": self._text(payload.get("exit_reason")),
            "result": self._enum(result, TRADE_RESULTS, "UNKNOWN"),
            "created_at": created_at,
            "updated_at": now,
            "notes": self._text(payload.get("notes")),
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def _upsert_trade(self, trade: dict[str, Any]) -> dict[str, Any]:
        store = self._read_store()
        trades = store.get("trades", [])
        updated = False
        for index, existing in enumerate(trades):
            if existing.get("trade_id") == trade["trade_id"]:
                merged = {**existing, **trade, "created_at": existing.get("created_at", trade["created_at"])}
                trades[index] = merged
                trade = merged
                updated = True
                break
        if not updated:
            trades.append(trade)
        store["trades"] = trades
        self._write_store(store)
        return trade

    def _read_store(self) -> dict[str, Any]:
        if not self.journal_path.exists():
            return {"trades": []}
        try:
            data = json.loads(self.journal_path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("trades"), list):
                return data
        except json.JSONDecodeError:
            return {"trades": []}
        return {"trades": []}

    def _find_by_mt5_ticket(self, ticket: str) -> dict[str, Any] | None:
        if not ticket:
            return None
        return next((trade for trade in self.list_trades(limit=100000) if self._text(trade.get("mt5_ticket")) == ticket), None)

    def _write_store(self, store: dict[str, Any]) -> None:
        self.journal_path.parent.mkdir(parents=True, exist_ok=True)
        self.journal_path.write_text(json.dumps(store, indent=2, sort_keys=True), encoding="utf-8")

    def _closed_result(self, payload: dict[str, Any]) -> str:
        explicit = self._text(payload.get("result")).upper()
        if explicit in TRADE_RESULTS:
            return explicit
        pnl = self._number_or_none(payload.get("profit_loss"))
        if pnl is None:
            return "UNKNOWN"
        if pnl > 0:
            return "WIN"
        if pnl < 0:
            return "LOSS"
        return "BREAKEVEN"

    def _enum(self, value: Any, allowed: set[str], fallback: str) -> str:
        text = self._text(value).upper()
        return text if text in allowed else fallback

    def _text(self, value: Any) -> str:
        return "" if value is None else str(value).strip()

    def _number_or_none(self, value: Any) -> float | None:
        if value in (None, ""):
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if number == number else None
