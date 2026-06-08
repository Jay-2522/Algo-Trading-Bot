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


class MT5TradeCloseSyncService:
    """Read-only MT5 demo close synchronization into realized journal P&L."""

    def __init__(self, persistent_trade_journal_service: Any | None = None) -> None:
        self.persistent_trade_journal_service = persistent_trade_journal_service or PersistentTradeJournalService()
        self._latest: dict[str, Any] = self._empty_result("NOT_SYNCED", "Close sync has not run yet.")
        self._history: list[dict[str, Any]] = []

    def get_status(self) -> dict[str, Any]:
        return {
            "status": "READY" if mt5 is not None else "UNAVAILABLE",
            "environment": "DEMO",
            "mt5_installed": mt5 is not None,
            "reason": "" if mt5 is not None else f"MetaTrader5 package unavailable: {MT5_IMPORT_ERROR}",
            **self._safety_flags(),
        }

    def run(self) -> dict[str, Any]:
        state = self._read_mt5_state()
        if state.get("status") != "READY":
            self._latest = {**state, "analytics": self.get_analytics()}
            self._history.append(self._latest)
            return self._latest

        open_positions = state["open_positions"]
        deals = state["deals"]
        account = state["account"]
        open_trades = [trade for trade in self.persistent_trade_journal_service.get_open_trades() if trade.get("source") == "MT5_DEMO" and trade.get("mt5_ticket")]
        closed: list[dict[str, Any]] = []
        unchanged: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []

        for trade in open_trades:
            if self._is_still_open(trade, open_positions, account):
                unchanged.append({"trade_id": trade["trade_id"], "mt5_ticket": trade["mt5_ticket"], "status": "OPEN"})
                continue
            close_deal = self._find_close_deal(trade, deals)
            if close_deal is None:
                warning = {"trade_id": trade["trade_id"], "mt5_ticket": trade["mt5_ticket"], "warning": "CLOSE_HISTORY_NOT_FOUND"}
                unchanged.append({**warning, "status": "OPEN"})
                warnings.append(warning)
                continue
            close_payload = self._close_payload(trade, close_deal, account)
            updated = self.persistent_trade_journal_service.mark_trade_closed_by_ticket(trade["mt5_ticket"], close_payload)
            if updated is not None:
                closed.append(updated)

        self._latest = {
            "status": "SYNCED",
            "environment": "DEMO",
            "open_trades_checked": len(open_trades),
            "closed_trades_updated": len(closed),
            "closed_trades": closed,
            "unchanged_trades": unchanged,
            "warnings": warnings,
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
        summary = self.persistent_trade_journal_service.calculate_realized_summary()
        return {
            **summary,
            "realized_pnl": summary["net_pnl"],
            "avg_pnl": round(summary["net_pnl"] / summary["closed_demo_trades"], 2) if summary["closed_demo_trades"] else 0.0,
            "data_source": "persistent_trade_journal_closed_trades",
            "message": "No closed demo trades yet." if summary["closed_demo_trades"] == 0 else "Realized P&L derived from closed MT5 demo trades.",
            **self._safety_flags(),
        }

    def _read_mt5_state(self) -> dict[str, Any]:
        if mt5 is None:
            return self._empty_result("UNAVAILABLE", f"MetaTrader5 package unavailable: {MT5_IMPORT_ERROR}")
        initialized = False
        try:
            initialized = bool(mt5.initialize())
            if not initialized:
                return self._empty_result("NOT_CONNECTED", f"MT5 initialize failed: {mt5.last_error()}")
            account = mt5.account_info()
            if not self._is_demo_account(account):
                return self._empty_result("NON_DEMO_ACCOUNT", "MT5 account is not confirmed as DEMO.")
            raw_positions = mt5.positions_get() or []
            now = datetime.now(timezone.utc)
            since = now - timedelta(days=30)
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
            return self._empty_result("READ_FAILED", f"MT5 close sync read failed: {exc}")
        finally:
            if initialized:
                mt5.shutdown()

    def _is_still_open(self, trade: dict[str, Any], positions: list[dict[str, Any]], account: Any) -> bool:
        ticket = str(trade.get("mt5_ticket") or "")
        symbol = str(trade.get("symbol") or "").upper()
        lot = self._float_or_zero(trade.get("lot"))
        account_login = str(trade.get("account_login") or getattr(account, "login", "") or "")
        for position in positions:
            if str(position.get("ticket")) != ticket:
                continue
            if str(position.get("symbol") or "").upper() != symbol:
                continue
            if abs(self._float_or_zero(position.get("volume")) - lot) >= 0.0000001:
                continue
            if account_login and str(position.get("account_login") or "") != account_login:
                continue
            return True
        return False

    def _find_close_deal(self, trade: dict[str, Any], deals: list[Any]) -> Any | None:
        ticket = str(trade.get("mt5_ticket") or "")
        symbol = str(trade.get("symbol") or "").upper()
        lot = self._float_or_zero(trade.get("lot"))
        candidates = []
        for deal in deals:
            deal_ticket_values = {
                str(getattr(deal, "position_id", "") or ""),
                str(getattr(deal, "order", "") or ""),
                str(getattr(deal, "ticket", "") or ""),
            }
            if ticket not in deal_ticket_values:
                continue
            if str(getattr(deal, "symbol", "") or "").upper() != symbol:
                continue
            if abs(self._float_or_zero(getattr(deal, "volume", 0.0)) - lot) >= 0.0000001:
                continue
            if self._is_close_deal(deal):
                candidates.append(deal)
        return sorted(candidates, key=lambda item: self._int_or_zero(getattr(item, "time", 0)))[-1] if candidates else None

    def _close_payload(self, trade: dict[str, Any], deal: Any, account: Any) -> dict[str, Any]:
        realized_pnl = self._float_or_zero(getattr(deal, "profit", 0.0))
        commission = self._float_or_zero(getattr(deal, "commission", 0.0))
        swap = self._float_or_zero(getattr(deal, "swap", 0.0))
        net_pnl = round(realized_pnl + commission + swap, 2)
        close_price = self._float_or_zero(getattr(deal, "price", 0.0))
        closed_at = self._deal_time_iso(getattr(deal, "time", 0))
        return {
            "close_price": close_price,
            "closed_at": closed_at,
            "close_time": closed_at,
            "realized_pnl": realized_pnl,
            "commission": commission,
            "swap": swap,
            "total_pnl": net_pnl,
            "net_pnl": net_pnl,
            "profit_loss": net_pnl,
            "result": self._result_from_pnl(net_pnl),
            "duration_minutes": self._duration_minutes(trade.get("opened_at"), closed_at),
            "exit_reason": self._exit_reason(trade, close_price),
            "account_login": str(trade.get("account_login") or getattr(account, "login", "") or ""),
            "server": str(trade.get("server") or getattr(account, "server", "") or ""),
            "notes": f"{trade.get('notes', '')} Close synchronized from MT5 history.".strip(),
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
        close_entries = {getattr(mt5, "DEAL_ENTRY_OUT", None), getattr(mt5, "DEAL_ENTRY_OUT_BY", None)}
        close_entries = {item for item in close_entries if item is not None}
        if close_entries:
            return entry in close_entries
        return self._float_or_zero(getattr(deal, "profit", 0.0)) != 0.0

    def _exit_reason(self, trade: dict[str, Any], close_price: float) -> str:
        stop_loss = self._float_or_zero(trade.get("stop_loss"))
        take_profit = self._float_or_zero(trade.get("take_profit"))
        tolerance = 0.0001
        if take_profit and abs(close_price - take_profit) <= tolerance:
            return "TAKE_PROFIT"
        if stop_loss and abs(close_price - stop_loss) <= tolerance:
            return "STOP_LOSS"
        return "UNKNOWN"

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

    def _empty_result(self, status: str, message: str) -> dict[str, Any]:
        return {
            "status": status,
            "environment": "DEMO",
            "message": message,
            "open_trades_checked": 0,
            "closed_trades_updated": 0,
            "closed_trades": [],
            "unchanged_trades": [],
            "warnings": [],
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
