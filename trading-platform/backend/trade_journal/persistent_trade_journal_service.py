from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_JOURNAL_PATH = PROJECT_ROOT / "data" / "trade_journal" / "trade_journal.json"
DEFAULT_VALIDATION_ROUNDS_PATH = PROJECT_ROOT / "data" / "validation_rounds"

TRADE_SOURCES = {"MT5_DEMO", "SIMULATION", "FUTURE_BROKER"}
TRADE_STATUSES = {"PLANNED", "SENT", "OPEN", "CLOSURE_PENDING", "CLOSURE_UNCONFIRMED", "CLOSED", "REJECTED", "CANCELLED"}
TRADE_RESULTS = {"WIN", "LOSS", "BREAKEVEN", "OPEN", "REJECTED", "UNKNOWN"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class PersistentTradeJournalService:
    """File-backed trade journal for explicit demo/simulation lifecycle records."""

    def __init__(self, journal_path: Path | None = None, validation_rounds_path: Path | None = None) -> None:
        self.journal_path = journal_path or DEFAULT_JOURNAL_PATH
        self.validation_rounds_path = validation_rounds_path or DEFAULT_VALIDATION_ROUNDS_PATH

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

    def mark_trade_closure_pending_by_ticket(self, ticket: str | int, payload: dict[str, Any] | None = None) -> dict[str, Any] | None:
        existing = self.get_trade_by_ticket(ticket)
        if existing is None:
            return None
        payload = payload or {}
        merged = {
            **existing,
            "status": "CLOSURE_PENDING",
            "result": "OPEN",
            "closure_pending": True,
            "closure_pending_reason": self._text(payload.get("closure_pending_reason")) or "MT5 open position disappeared; waiting for MT5 close history.",
            "closure_pending_at": self._text(payload.get("closure_pending_at")) or existing.get("closure_pending_at") or utc_now_iso(),
            "last_closure_lookup_at": self._text(payload.get("last_closure_lookup_at")) or utc_now_iso(),
            "updated_at": utc_now_iso(),
        }
        return self._upsert_trade(merged)

    def mark_trade_closure_unconfirmed_by_ticket(self, ticket: str | int, payload: dict[str, Any] | None = None) -> dict[str, Any] | None:
        existing = self.get_trade_by_ticket(ticket)
        if existing is None:
            return None
        payload = payload or {}
        merged = {
            **existing,
            "status": "CLOSURE_UNCONFIRMED",
            "result": "OPEN",
            "closure_pending": True,
            "mt5_closure_confirmed": False,
            "closure_pending_reason": self._text(payload.get("closure_pending_reason")) or f"Ticket {ticket} disappeared from open positions but MT5 history did not confirm closure yet.",
            "closure_pending_at": self._text(payload.get("closure_pending_at")) or existing.get("closure_pending_at") or utc_now_iso(),
            "last_closure_lookup_at": self._text(payload.get("last_closure_lookup_at")) or utc_now_iso(),
            "updated_at": utc_now_iso(),
        }
        return self._upsert_trade(merged)

    def record_exit_management_update(self, ticket: str | int, payload: dict[str, Any]) -> dict[str, Any] | None:
        existing = self.get_trade_by_ticket(ticket)
        if existing is None:
            return None
        merged = {
            **existing,
            "exit_management": payload.get("exit_management") or existing.get("exit_management") or {},
            "exit_reason": self._text(payload.get("exit_reason")) or existing.get("exit_reason", ""),
            "notes": self._text(payload.get("notes")) or existing.get("notes", ""),
            "updated_at": utc_now_iso(),
        }
        return self._upsert_trade(merged)

    def get_open_trades(self) -> list[dict[str, Any]]:
        return [trade for trade in self.list_trades(limit=100000) if trade.get("status") in {"OPEN", "CLOSURE_PENDING", "CLOSURE_UNCONFIRMED"}]

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

    def get_all_time_trades(self, limit: int = 100000) -> list[dict[str, Any]]:
        """Aggregate every locally persisted trade lifecycle row, across active and archived rounds."""
        records: list[dict[str, Any]] = []
        for trade in self.list_trades(limit=100000):
            records.append(self._normalize_history_trade(trade, source="trade_journal"))
        records.extend(self._archived_round_trades())
        deduped: dict[str, dict[str, Any]] = {}
        for trade in records:
            key = self._dedupe_key(trade)
            existing = deduped.get(key)
            if existing is None or self._trade_preference_score(trade) >= self._trade_preference_score(existing):
                deduped[key] = trade
        sorted_records = sorted(deduped.values(), key=self._trade_sort_time, reverse=True)
        return sorted_records[: max(1, limit)]

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

    def _archived_round_trades(self) -> list[dict[str, Any]]:
        if not self.validation_rounds_path.exists():
            return []
        records: list[dict[str, Any]] = []
        for path in sorted(self.validation_rounds_path.glob("*.json")):
            if path.name == "rounds_index.json":
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict):
                continue
            session = payload.get("session") if isinstance(payload.get("session"), dict) else {}
            session_id = self._text(payload.get("session_id") or payload.get("active_session_id") or session.get("session_id"))
            round_label = self._text(payload.get("round_label") or session.get("round_label"))
            round_number = payload.get("round_number")
            for collection_name in ("trades", "closed_trades", "all_trades", "trade_journal"):
                collection = payload.get(collection_name)
                if isinstance(collection, list):
                    for trade in collection:
                        if isinstance(trade, dict):
                            records.append(
                                self._normalize_history_trade(
                                    {
                                        **trade,
                                        "validation_session_id": self._text(trade.get("validation_session_id") or trade.get("session_id")) or session_id,
                                        "round_label": self._text(trade.get("round_label")) or round_label,
                                        "round_number": trade.get("round_number") if trade.get("round_number") is not None else round_number,
                                    },
                                    source=f"validation_rounds/{path.name}",
                                )
                            )
        return records

    def _normalize_history_trade(self, trade: dict[str, Any], source: str) -> dict[str, Any]:
        normalized = dict(trade)
        ticket = self._text(normalized.get("mt5_ticket") or normalized.get("ticket"))
        session_id = self._text(normalized.get("validation_session_id") or normalized.get("session_id"))
        round_label = self._text(normalized.get("round_label") or normalized.get("round"))
        if not round_label:
            round_label = self._round_label_for_session(session_id)
        normalized.update(
            {
                "ticket": ticket or self._text(normalized.get("trade_id")),
                "mt5_ticket": ticket,
                "validation_session_id": session_id,
                "session_id": session_id,
                "round_label": round_label,
                "round": self._display_round_label(round_label, session_id),
                "symbol": self._text(normalized.get("symbol")).upper(),
                "side": self._text(normalized.get("side") or normalized.get("type") or normalized.get("direction")).upper(),
                "status": self._text(normalized.get("status") or ("CLOSED" if normalized.get("closed_at") else "OPEN")).upper(),
                "result": self._text(normalized.get("result") or ("OPEN" if not normalized.get("closed_at") else "UNKNOWN")).upper(),
                "history_source": source,
            }
        )
        return normalized

    def _round_label_for_session(self, session_id: str) -> str:
        if not session_id or not self.validation_rounds_path.exists():
            return ""
        path = self.validation_rounds_path / f"round_{session_id}.json"
        if not path.exists():
            return ""
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return ""
        if not isinstance(payload, dict):
            return ""
        session = payload.get("session") if isinstance(payload.get("session"), dict) else {}
        return self._text(payload.get("round_label") or session.get("round_label"))

    def _display_round_label(self, round_label: str, session_id: str) -> str:
        label = self._text(round_label)
        if label.upper().startswith("ROUND_"):
            suffix = label.split("_", 1)[1]
            return f"Round {suffix}" if suffix else label
        if label:
            return label.replace("_", " ").title()
        return "Validation" if session_id else "Manual"

    def _dedupe_key(self, trade: dict[str, Any]) -> str:
        ticket = self._text(trade.get("mt5_ticket") or trade.get("ticket"))
        if ticket:
            return f"ticket:{ticket}"
        trade_id = self._text(trade.get("trade_id") or trade.get("id"))
        if trade_id:
            return f"trade:{trade_id}"
        return f"row:{self._text(trade.get('validation_session_id'))}:{self._text(trade.get('symbol'))}:{self._text(trade.get('opened_at') or trade.get('created_at'))}"

    def _trade_preference_score(self, trade: dict[str, Any]) -> tuple[int, str]:
        status = self._text(trade.get("status")).upper()
        status_score = 3 if status == "CLOSED" else 2 if status in {"OPEN", "SENT", "PENDING"} else 1
        completeness = sum(1 for key in ("entry_price", "close_price", "stop_loss", "take_profit", "net_pnl", "opened_at", "closed_at") if trade.get(key) not in (None, ""))
        return (status_score * 100 + completeness, self._trade_sort_time(trade))

    def _trade_sort_time(self, trade: dict[str, Any]) -> str:
        return self._text(trade.get("updated_at") or trade.get("closed_at") or trade.get("close_time") or trade.get("opened_at") or trade.get("open_time") or trade.get("created_at"))

    def clear_test_data_only(self) -> dict[str, Any]:
        self._write_store({"trades": []})
        return {"status": "CLEARED_TEST_DATA_ONLY", "record_count": 0}

    def clear_session_trades_by_status(self, session_id: str, statuses: set[str]) -> dict[str, Any]:
        normalized_session = self._text(session_id)
        normalized_statuses = {self._text(status).upper() for status in statuses if self._text(status)}
        if not normalized_session or not normalized_statuses:
            return {"status": "NOOP", "session_id": normalized_session, "removed_count": 0, "remaining_count": len(self.list_trades(limit=100000))}
        store = self._read_store()
        trades = store.get("trades", [])
        kept: list[dict[str, Any]] = []
        removed: list[dict[str, Any]] = []
        for trade in trades:
            trade_session = self._text(trade.get("validation_session_id") or trade.get("session_id"))
            trade_status = self._text(trade.get("status")).upper()
            if trade_session == normalized_session and trade_status in normalized_statuses:
                removed.append(trade)
            else:
                kept.append(trade)
        store["trades"] = kept
        self._write_store(store)
        return {
            "status": "CLEARED_SESSION_TRADES",
            "session_id": normalized_session,
            "statuses": sorted(normalized_statuses),
            "removed_count": len(removed),
            "remaining_count": len(kept),
            "removed_tickets": [self._text(trade.get("mt5_ticket") or trade.get("ticket")) for trade in removed if self._text(trade.get("mt5_ticket") or trade.get("ticket"))],
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def exclude_session_trades_from_active_stats(self, session_id: str, statuses: set[str], reason: str = "manual_dashboard_reset") -> dict[str, Any]:
        normalized_session = self._text(session_id)
        normalized_statuses = {self._text(status).upper() for status in statuses if self._text(status)}
        if not normalized_session or not normalized_statuses:
            return {"status": "NOOP", "session_id": normalized_session, "excluded_count": 0, "trade_count": len(self.list_trades(limit=100000))}
        store = self._read_store()
        trades = store.get("trades", [])
        excluded: list[dict[str, Any]] = []
        now = utc_now_iso()
        for trade in trades:
            trade_session = self._text(trade.get("validation_session_id") or trade.get("session_id"))
            trade_status = self._text(trade.get("status")).upper()
            if trade_session == normalized_session and trade_status in normalized_statuses:
                trade["active_stats_excluded"] = True
                trade["active_stats_excluded_at"] = now
                trade["active_stats_excluded_reason"] = self._text(reason)
                trade["updated_at"] = now
                excluded.append(trade)
        store["trades"] = trades
        self._write_store(store)
        return {
            "status": "EXCLUDED_SESSION_TRADES_FROM_ACTIVE_STATS",
            "session_id": normalized_session,
            "statuses": sorted(normalized_statuses),
            "excluded_count": len(excluded),
            "trade_count": len(trades),
            "excluded_tickets": [self._text(trade.get("mt5_ticket") or trade.get("ticket")) for trade in excluded if self._text(trade.get("mt5_ticket") or trade.get("ticket"))],
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def _base_record(self, payload: dict[str, Any], status: str, result: str) -> dict[str, Any]:
        now = utc_now_iso()
        existing = self.get_trade(str(payload.get("trade_id"))) if payload.get("trade_id") else None
        created_at = existing.get("created_at") if existing else now
        strategy_metadata = payload.get("strategy_metadata") if isinstance(payload.get("strategy_metadata"), dict) else (existing or {}).get("strategy_metadata", {})
        strategy_profile = self._text(payload.get("strategy_profile")) or self._text(strategy_metadata.get("strategy_profile")) or (existing or {}).get("strategy_profile", "")
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
            "decision_reason": self._text(payload.get("decision_reason") or payload.get("final_decision_reason")) or (existing or {}).get("decision_reason", ""),
            "final_decision_reason": self._text(payload.get("final_decision_reason")) or (existing or {}).get("final_decision_reason", ""),
            "final_decision": payload.get("final_decision") if isinstance(payload.get("final_decision"), dict) else (existing or {}).get("final_decision", {}),
            "score_components": payload.get("score_components") if isinstance(payload.get("score_components"), dict) else (existing or {}).get("score_components", {}),
            "passed_rules": payload.get("passed_rules") if isinstance(payload.get("passed_rules"), list) else (existing or {}).get("passed_rules", []),
            "failed_rules": payload.get("failed_rules") if isinstance(payload.get("failed_rules"), list) else (existing or {}).get("failed_rules", []),
            "advisory_warnings": payload.get("advisory_warnings") if isinstance(payload.get("advisory_warnings"), list) else (existing or {}).get("advisory_warnings", []),
            "confirmation_score": self._number_or_none(payload.get("confirmation_score")) if payload.get("confirmation_score") is not None else (existing or {}).get("confirmation_score"),
            "confirmation_required": self._number_or_none(payload.get("confirmation_required")) if payload.get("confirmation_required") is not None else (existing or {}).get("confirmation_required"),
            "confirmation_total": self._number_or_none(payload.get("confirmation_total")) if payload.get("confirmation_total") is not None else (existing or {}).get("confirmation_total"),
            "confirmation_passed": payload.get("confirmation_passed") if isinstance(payload.get("confirmation_passed"), list) else (existing or {}).get("confirmation_passed", []),
            "confirmation_missing": payload.get("confirmation_missing") if isinstance(payload.get("confirmation_missing"), list) else (existing or {}).get("confirmation_missing", []),
            "adaptive_level": self._number_or_none(payload.get("adaptive_level")) if payload.get("adaptive_level") is not None else (existing or {}).get("adaptive_level"),
            "adaptive_strategy_level": self._number_or_none(payload.get("adaptive_strategy_level")) if payload.get("adaptive_strategy_level") is not None else (existing or {}).get("adaptive_strategy_level"),
            "active_stats_excluded": bool(payload.get("active_stats_excluded")) if payload.get("active_stats_excluded") is not None else bool((existing or {}).get("active_stats_excluded", False)),
            "active_stats_excluded_at": self._text(payload.get("active_stats_excluded_at")) or (existing or {}).get("active_stats_excluded_at", ""),
            "active_stats_excluded_reason": self._text(payload.get("active_stats_excluded_reason")) or (existing or {}).get("active_stats_excluded_reason", ""),
            "legacy_path_loss": bool(payload.get("legacy_path_loss")) if payload.get("legacy_path_loss") is not None else bool((existing or {}).get("legacy_path_loss", False)),
            "legacy_execution_audit": payload.get("legacy_execution_audit") if isinstance(payload.get("legacy_execution_audit"), dict) else (existing or {}).get("legacy_execution_audit", {}),
            "strategy_profile": strategy_profile,
            "strategy_metadata": strategy_metadata,
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
            "mt5_closure_confirmed": bool(payload.get("mt5_closure_confirmed")) if payload.get("mt5_closure_confirmed") is not None else bool((existing or {}).get("mt5_closure_confirmed", False)),
            "mt5_close_deal_ticket": self._text(payload.get("mt5_close_deal_ticket")) or (existing or {}).get("mt5_close_deal_ticket", ""),
            "mt5_close_order_ticket": self._text(payload.get("mt5_close_order_ticket")) or (existing or {}).get("mt5_close_order_ticket", ""),
            "mt5_position_id": self._text(payload.get("mt5_position_id")) or (existing or {}).get("mt5_position_id", ""),
            "mt5_deal_entry": self._text(payload.get("mt5_deal_entry")) or (existing or {}).get("mt5_deal_entry", ""),
            "mt5_deal_reason": self._text(payload.get("mt5_deal_reason")) or (existing or {}).get("mt5_deal_reason", ""),
            "closure_source": self._text(payload.get("closure_source")) or (existing or {}).get("closure_source", ""),
            "autopsy": payload.get("autopsy") if isinstance(payload.get("autopsy"), dict) else (existing or {}).get("autopsy", {}),
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
