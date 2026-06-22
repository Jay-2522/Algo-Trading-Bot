from datetime import datetime, timedelta, timezone
from typing import Any

from backend.trade_journal.persistent_trade_journal_service import PersistentTradeJournalService

try:
    import MetaTrader5 as mt5
except Exception as exc:  # pragma: no cover - depends on local MT5 installation
    mt5 = None
    MT5_IMPORT_ERROR = exc
else:
    MT5_IMPORT_ERROR = None


class MT5TradeLifecycleService:
    """Read-only lifecycle sync for MT5 demo trades already in the journal."""

    def __init__(self, persistent_trade_journal_service: Any | None = None) -> None:
        self.persistent_trade_journal_service = persistent_trade_journal_service or PersistentTradeJournalService()
        self._latest: dict[str, Any] = self._empty_sync("NOT_SYNCED", "Lifecycle sync has not run yet.")
        self._history: list[dict[str, Any]] = []

    def get_status(self) -> dict[str, Any]:
        return {
            "status": "READY" if mt5 is not None else "UNAVAILABLE",
            "environment": "DEMO",
            "mt5_installed": mt5 is not None,
            "reason": "" if mt5 is not None else f"MetaTrader5 package unavailable: {MT5_IMPORT_ERROR}",
            **self._safety_flags(),
        }

    def sync(self) -> dict[str, Any]:
        mt5_state = self._read_mt5_state()
        if mt5_state.get("status") not in {"READY"}:
            self._latest = {**mt5_state, "updated_trades": [], "unchanged_trades": [], "analytics": self.get_analytics()}
            self._history.append(self._latest)
            return self._latest

        open_positions = mt5_state["open_positions"]
        deals = mt5_state["deals"]
        orders = mt5_state["orders"]
        account = mt5_state["account"]
        open_trades = [
            trade
            for trade in self.persistent_trade_journal_service.list_trades(limit=100000)
            if trade.get("source") == "MT5_DEMO" and trade.get("status") == "OPEN" and trade.get("mt5_ticket")
        ]
        updated_trades: list[dict[str, Any]] = []
        unchanged_trades: list[dict[str, Any]] = []

        for trade in open_trades:
            if self._matching_open_position(trade, open_positions, account):
                unchanged_trades.append({"trade_id": trade["trade_id"], "mt5_ticket": trade["mt5_ticket"], "status": "OPEN"})
                continue
            close_deal = self._matching_close_deal(trade, deals, orders, account)
            if close_deal is None:
                unchanged_trades.append({"trade_id": trade["trade_id"], "mt5_ticket": trade["mt5_ticket"], "status": "OPEN", "reason": "NO_MATCHING_MT5_CLOSE"})
                continue
            updated_trades.append(self.persistent_trade_journal_service.record_trade_closed(self._closed_payload(trade, close_deal, account)))

        self._latest = {
            "status": "SYNCED",
            "environment": "DEMO",
            "open_trades_checked": len(open_trades),
            "history_deals_checked": len(deals),
            "history_orders_checked": len(orders),
            "closed_trades_updated": len(updated_trades),
            "updated_trades": updated_trades,
            "unchanged_trades": unchanged_trades,
            "analytics": self.get_analytics(),
            "timestamp": self._timestamp(),
            **self._safety_flags(),
        }
        self._history.append(self._latest)
        return self._latest

    def get_latest(self) -> dict[str, Any]:
        return self._latest

    def get_history(self, limit: int = 100) -> list[dict[str, Any]]:
        return self._history[-limit:]

    def get_analytics(self) -> dict[str, Any]:
        trades = [trade for trade in self.persistent_trade_journal_service.list_trades(limit=100000) if trade.get("source") == "MT5_DEMO"]
        closed = [trade for trade in trades if trade.get("status") == "CLOSED"]
        wins = [trade for trade in closed if trade.get("result") == "WIN"]
        losses = [trade for trade in closed if trade.get("result") == "LOSS"]
        pnl_values = [self._float_or_zero(trade.get("profit_loss")) for trade in closed]
        durations = [self._float_or_zero(trade.get("duration_minutes")) for trade in closed if trade.get("duration_minutes") not in (None, "")]
        rr_values = [self._float_or_zero(trade.get("risk_reward_ratio")) for trade in trades if trade.get("risk_reward_ratio") is not None]
        return {
            "status": "READY",
            "environment": "DEMO",
            "total_trades": len(trades),
            "closed_trades": len(closed),
            "open_trades": len([trade for trade in trades if trade.get("status") == "OPEN"]),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round((len(wins) / len(closed)) * 100, 2) if closed else 0.0,
            "net_pnl": round(sum(pnl_values), 2) if pnl_values else 0.0,
            "avg_pnl": round(sum(pnl_values) / len(pnl_values), 2) if pnl_values else 0.0,
            "avg_duration": round(sum(durations) / len(durations), 2) if durations else 0.0,
            "avg_rr": round(sum(rr_values) / len(rr_values), 2) if rr_values else 0.0,
            **self._safety_flags(),
        }

    def _read_mt5_state(self) -> dict[str, Any]:
        if mt5 is None:
            return self._empty_sync("UNAVAILABLE", f"MetaTrader5 package unavailable: {MT5_IMPORT_ERROR}")
        initialized = False
        try:
            initialized = bool(mt5.initialize())
            if not initialized:
                return self._empty_sync("NOT_CONNECTED", f"MT5 initialize failed: {mt5.last_error()}")
            account = mt5.account_info()
            if not self._is_demo_account(account):
                return self._empty_sync("NON_DEMO_ACCOUNT", "MT5 account is not confirmed as DEMO.")
            raw_positions = mt5.positions_get() or []
            since, now = self._history_range()
            deals = mt5.history_deals_get(since, now) or []
            orders = mt5.history_orders_get(since, now) or []
            return {
                "status": "READY",
                "account": account,
                "open_positions": [self._normalize_position(position, account) for position in raw_positions],
                "deals": list(deals),
                "orders": list(orders),
                **self._safety_flags(),
            }
        except Exception as exc:  # pragma: no cover - depends on terminal state
            return self._empty_sync("READ_FAILED", f"MT5 lifecycle read failed: {exc}")
        finally:
            if initialized:
                mt5.shutdown()

    def _matching_open_position(self, trade: dict[str, Any], positions: list[dict[str, Any]], account: Any) -> dict[str, Any] | None:
        ticket = str(trade.get("mt5_ticket") or "")
        symbol = str(trade.get("symbol") or "").upper()
        lot = self._float_or_zero(trade.get("lot"))
        account_login = str(trade.get("account_login") or getattr(account, "login", "") or "")
        for position in positions:
            if (
                str(position.get("ticket")) == ticket
                and str(position.get("symbol") or "").upper() == symbol
                and abs(self._float_or_zero(position.get("volume")) - lot) < 0.0000001
                and (not account_login or str(position.get("account_login") or "") == account_login)
            ):
                return position
        return None

    def _matching_close_deal(self, trade: dict[str, Any], deals: list[Any], orders: list[Any], account: Any) -> Any | None:
        ticket = str(trade.get("mt5_ticket") or "")
        symbol = str(trade.get("symbol") or "").upper()
        lot = self._float_or_zero(trade.get("lot"))
        related_ticket_values = self._related_ticket_values(ticket, deals, orders)
        close_candidates = []
        for deal in deals:
            deal_ticket_values = self._deal_ticket_values(deal)
            deal_symbol = str(getattr(deal, "symbol", "") or "").upper()
            deal_volume = self._float_or_zero(getattr(deal, "volume", 0.0))
            if related_ticket_values.intersection(deal_ticket_values) and deal_symbol == symbol and abs(deal_volume - lot) < 0.0000001:
                if self._is_close_deal(deal):
                    close_candidates.append(deal)
        return sorted(close_candidates, key=lambda item: self._int_or_zero(getattr(item, "time", 0)))[-1] if close_candidates else None

    def _related_ticket_values(self, ticket: str, deals: list[Any], orders: list[Any]) -> set[str]:
        related = {ticket} if ticket else set()
        changed = True
        while changed:
            changed = False
            for order in orders:
                values = self._order_ticket_values(order)
                if related.intersection(values) and not values.issubset(related):
                    related.update(values)
                    changed = True
            for deal in deals:
                values = self._deal_ticket_values(deal)
                if related.intersection(values) and not values.issubset(related):
                    related.update(values)
                    changed = True
        return {value for value in related if value}

    def _deal_ticket_values(self, deal: Any) -> set[str]:
        return {
            str(getattr(deal, "position_id", "") or ""),
            str(getattr(deal, "order", "") or ""),
            str(getattr(deal, "ticket", "") or ""),
        } - {""}

    def _order_ticket_values(self, order: Any) -> set[str]:
        return {
            str(getattr(order, "position_id", "") or ""),
            str(getattr(order, "position_by_id", "") or ""),
            str(getattr(order, "ticket", "") or ""),
        } - {""}

    def _closed_payload(self, trade: dict[str, Any], close_deal: Any, account: Any) -> dict[str, Any]:
        realized_pnl = self._float_or_zero(getattr(close_deal, "profit", 0.0))
        swap = self._float_or_zero(getattr(close_deal, "swap", 0.0))
        commission = self._float_or_zero(getattr(close_deal, "commission", 0.0))
        total_pnl = round(realized_pnl + swap + commission, 2)
        close_time = self._deal_time_iso(getattr(close_deal, "time", 0))
        duration = self._duration_minutes(trade.get("opened_at"), close_time)
        return {
            **trade,
            "close_price": self._float_or_zero(getattr(close_deal, "price", 0.0)),
            "closed_at": close_time,
            "close_time": close_time,
            "realized_pnl": realized_pnl,
            "swap": swap,
            "commission": commission,
            "total_pnl": total_pnl,
            "profit_loss": total_pnl,
            "result": self._result_from_pnl(total_pnl),
            "duration_minutes": duration,
            "exit_reason": self._exit_reason(trade, self._float_or_zero(getattr(close_deal, "price", 0.0)), close_deal),
            "mt5_closure_confirmed": True,
            "mt5_close_deal_ticket": str(getattr(close_deal, "ticket", "") or ""),
            "mt5_close_order_ticket": str(getattr(close_deal, "order", "") or ""),
            "mt5_position_id": str(getattr(close_deal, "position_id", "") or trade.get("mt5_ticket") or ""),
            "mt5_deal_entry": self._deal_constant_name("DEAL_ENTRY_", getattr(close_deal, "entry", None)),
            "mt5_deal_reason": self._deal_constant_name("DEAL_REASON_", getattr(close_deal, "reason", None)),
            "closure_source": "MT5_HISTORY_DEAL",
            "account_login": str(trade.get("account_login") or getattr(account, "login", "") or ""),
            "server": str(trade.get("server") or getattr(account, "server", "") or ""),
            "notes": f"{trade.get('notes', '')} Lifecycle closed from MT5 deal history.".strip(),
        }

    def _normalize_position(self, position: Any, account: Any) -> dict[str, Any]:
        return {
            "ticket": self._int_or_zero(getattr(position, "ticket", 0)),
            "symbol": str(getattr(position, "symbol", "") or "").upper(),
            "volume": self._float_or_zero(getattr(position, "volume", 0.0)),
            "account_login": str(getattr(account, "login", "") or ""),
        }

    def _is_close_deal(self, deal: Any) -> bool:
        entry = getattr(deal, "entry", None)
        close_entries = {
            getattr(mt5, "DEAL_ENTRY_OUT", None),
            getattr(mt5, "DEAL_ENTRY_OUT_BY", None),
        }
        close_entries = {item for item in close_entries if item is not None}
        if close_entries:
            return entry in close_entries
        return self._float_or_zero(getattr(deal, "profit", 0.0)) != 0.0

    def _history_range(self) -> tuple[datetime, datetime]:
        now = datetime.now(timezone.utc) + timedelta(days=1)
        opened_values = []
        for trade in self.persistent_trade_journal_service.get_open_trades():
            opened_at = trade.get("opened_at") or trade.get("created_at")
            parsed = self._parse_datetime(opened_at)
            if parsed is not None:
                opened_values.append(parsed)
        since = min(opened_values) - timedelta(days=1) if opened_values else datetime.now(timezone.utc) - timedelta(days=90)
        return since, now

    def _parse_datetime(self, value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

    def _exit_reason(self, trade: dict[str, Any], close_price: float, deal: Any) -> str:
        deal_reason = self._deal_constant_name("DEAL_REASON_", getattr(deal, "reason", None))
        if deal_reason == "SL":
            return "STOP_LOSS"
        if deal_reason == "TP":
            return "TAKE_PROFIT"
        if deal_reason in {"CLIENT", "MOBILE", "WEB"}:
            return "MANUAL"
        if deal_reason in {"SO", "ROLLOVER", "VMARGIN", "SPLIT"}:
            return "BROKER"
        stop_loss = self._float_or_zero(trade.get("stop_loss"))
        take_profit = self._float_or_zero(trade.get("take_profit"))
        tolerance = 0.0001
        if take_profit and abs(close_price - take_profit) <= tolerance:
            return "TAKE_PROFIT"
        if stop_loss and abs(close_price - stop_loss) <= tolerance:
            return "STOP_LOSS"
        return "UNKNOWN"

    def _deal_constant_name(self, prefix: str, value: Any) -> str:
        for name in dir(mt5):
            if name.startswith(prefix) and getattr(mt5, name, object()) == value:
                return name.replace(prefix, "")
        return str(value) if value is not None else "UNKNOWN"

    def _duration_minutes(self, opened_at: Any, closed_at: str) -> float | None:
        try:
            opened = datetime.fromisoformat(str(opened_at).replace("Z", "+00:00"))
            closed = datetime.fromisoformat(closed_at.replace("Z", "+00:00"))
            return round((closed - opened).total_seconds() / 60, 2)
        except (TypeError, ValueError):
            return None

    def _deal_time_iso(self, value: Any) -> str:
        timestamp = self._int_or_zero(value)
        if timestamp <= 0:
            return self._timestamp()
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()

    def _result_from_pnl(self, pnl: float) -> str:
        if pnl > 0:
            return "WIN"
        if pnl < 0:
            return "LOSS"
        return "BREAKEVEN"

    def _is_demo_account(self, account: Any) -> bool:
        if account is None:
            return False
        server = str(getattr(account, "server", "") or "")
        trade_mode = getattr(account, "trade_mode", None)
        demo_mode = getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", None)
        return "demo" in server.lower() or (demo_mode is not None and trade_mode == demo_mode)

    def _empty_sync(self, status: str, message: str) -> dict[str, Any]:
        return {
            "status": status,
            "environment": "DEMO",
            "message": message,
            "open_trades_checked": 0,
            "closed_trades_updated": 0,
            "updated_trades": [],
            "unchanged_trades": [],
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

    def _float_or_zero(self, value: Any) -> float:
        try:
            return float(value or 0.0)
        except (TypeError, ValueError):
            return 0.0

    def _int_or_zero(self, value: Any) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()
