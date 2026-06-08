from datetime import datetime, timezone
from typing import Any

from backend.mt5_demo.mt5_demo_position_sync_service import MT5DemoPositionSyncService
from backend.trade_journal.persistent_trade_journal_service import PersistentTradeJournalService


class MT5PositionMonitoringService:
    """Join read-only MT5 demo open positions with persistent journal state."""

    def __init__(
        self,
        position_sync_service: MT5DemoPositionSyncService | None = None,
        persistent_trade_journal_service: Any | None = None,
    ) -> None:
        self.position_sync_service = position_sync_service or MT5DemoPositionSyncService()
        self.persistent_trade_journal_service = persistent_trade_journal_service or PersistentTradeJournalService()
        self._latest: dict[str, Any] = self._empty_monitor("NOT_SYNCED", "Position monitor has not synced yet.")

    def get_status(self) -> dict[str, Any]:
        return {
            "status": "READY",
            "environment": "DEMO",
            "data_sources": ["MT5_DEMO_POSITIONS", "PERSISTENT_TRADE_JOURNAL"],
            "last_sync_time": self._latest.get("timestamp"),
            **self._safety_flags(),
        }

    def get_open_positions(self) -> dict[str, Any]:
        return self._build_monitor()

    def get_open_positions_by_symbol(self, symbol: str) -> dict[str, Any]:
        normalized_symbol = str(symbol or "").strip().upper()
        monitor = self._build_monitor(symbol=normalized_symbol)
        return {**monitor, "symbol": normalized_symbol}

    def get_position_by_ticket(self, ticket: str | int) -> dict[str, Any]:
        ticket_text = str(ticket or "").strip()
        monitor = self._build_monitor()
        position = next((item for item in monitor["positions"] if str(item.get("ticket")) == ticket_text), None)
        if position is None:
            return {
                "status": "NOT_FOUND",
                "environment": "DEMO",
                "ticket": ticket_text,
                "position": None,
                "message": "No open MT5 demo position found for ticket.",
                **self._safety_flags(),
            }
        return {
            "status": "FOUND",
            "environment": "DEMO",
            "ticket": ticket_text,
            "position": position,
            **self._safety_flags(),
        }

    def sync(self) -> dict[str, Any]:
        self.position_sync_service.sync_journal()
        self._latest = self._build_monitor()
        return self._latest

    def _build_monitor(self, symbol: str | None = None) -> dict[str, Any]:
        mt5_result = self.position_sync_service.get_open_positions_by_symbol(symbol) if symbol else self.position_sync_service.get_open_positions()
        if mt5_result.get("status") not in {"POSITIONS_FOUND", "NO_OPEN_POSITIONS"}:
            return {
                **self._empty_monitor(mt5_result.get("status", "UNAVAILABLE"), mt5_result.get("message", "MT5 demo position read unavailable.")),
                "source_status": mt5_result.get("status"),
            }

        journal_records = self.persistent_trade_journal_service.list_trades(limit=100000)
        monitored = [self._monitor_position(position, journal_records) for position in mt5_result.get("positions", [])]
        return {
            "status": "POSITIONS_FOUND" if monitored else "NO_OPEN_POSITIONS",
            "environment": "DEMO",
            "positions_count": len(monitored),
            "positions": monitored,
            "empty_state": len(monitored) == 0,
            "message": "No open MT5 demo positions." if not monitored else "Open MT5 demo positions joined with journal records.",
            "timestamp": self._timestamp(),
            **self._safety_flags(),
        }

    def _monitor_position(self, position: dict[str, Any], journal_records: list[dict[str, Any]]) -> dict[str, Any]:
        journal = self._match_journal(position, journal_records)
        entry_price = self._float_or_none(position.get("price_open"))
        current_price = self._float_or_none(position.get("price_current"))
        stop_loss = self._float_or_none(position.get("sl"))
        take_profit = self._float_or_none(position.get("tp"))
        floating_pnl = self._float_or_none(position.get("profit")) or 0.0
        return {
            "ticket": position.get("ticket"),
            "symbol": position.get("symbol"),
            "side": position.get("type"),
            "lot": position.get("volume"),
            "entry_price": entry_price,
            "current_price": current_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "floating_pnl": floating_pnl,
            "floating_pnl_percent": None,
            "distance_to_sl": round(abs((current_price or 0.0) - stop_loss), 6) if current_price is not None and stop_loss is not None else None,
            "distance_to_tp": round(abs(take_profit - (current_price or 0.0)), 6) if current_price is not None and take_profit is not None else None,
            "lifecycle_status": "OPEN",
            "journal_status": str(journal.get("status", "NOT_JOURNALED")) if journal else "NOT_JOURNALED",
            "account_login": position.get("account_login"),
            "server": position.get("server"),
            "last_sync_time": self._timestamp(),
            "journal_trade_id": journal.get("trade_id") if journal else "",
            **self._safety_flags(),
        }

    def _match_journal(self, position: dict[str, Any], journal_records: list[dict[str, Any]]) -> dict[str, Any] | None:
        ticket = str(position.get("ticket") or "")
        symbol = str(position.get("symbol") or "").upper()
        account_login = str(position.get("account_login") or "")
        server = str(position.get("server") or "")
        for record in journal_records:
            if str(record.get("mt5_ticket") or "") != ticket:
                continue
            if str(record.get("symbol") or "").upper() != symbol:
                continue
            if account_login and str(record.get("account_login") or "") not in {"", account_login}:
                continue
            if server and str(record.get("server") or "") not in {"", server}:
                continue
            return record
        return None

    def _empty_monitor(self, status: str, message: str) -> dict[str, Any]:
        return {
            "status": status,
            "environment": "DEMO",
            "positions_count": 0,
            "positions": [],
            "empty_state": True,
            "message": message,
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
            "mt5_order_send_used": False,
        }

    def _float_or_none(self, value: Any) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()
