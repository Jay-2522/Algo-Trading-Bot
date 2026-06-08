from datetime import datetime, timezone
from typing import Any

from backend.trade_journal.persistent_trade_journal_service import PersistentTradeJournalService

try:
    import MetaTrader5 as mt5
except Exception as exc:  # pragma: no cover - depends on local MT5 installation
    mt5 = None
    MT5_IMPORT_ERROR = exc
else:
    MT5_IMPORT_ERROR = None


class MT5DemoPositionSyncService:
    """Read-only MT5 demo position sync into the persistent trade journal."""

    def __init__(self, persistent_trade_journal_service: Any | None = None) -> None:
        self.persistent_trade_journal_service = persistent_trade_journal_service or PersistentTradeJournalService()
        self._latest_sync: dict[str, Any] = self._empty_sync("NOT_SYNCED", "Position sync has not run yet.")

    def get_status(self) -> dict[str, Any]:
        if mt5 is None:
            return {
                "status": "UNAVAILABLE",
                "environment": "DEMO",
                "mt5_installed": False,
                "account_connected": False,
                "account_type": "DEMO",
                "open_positions_visible": False,
                "reason": f"MetaTrader5 package unavailable: {MT5_IMPORT_ERROR}",
                **self._safety_flags(),
            }
        return {
            "status": "READY",
            "environment": "DEMO",
            "mt5_installed": True,
            "account_connected": None,
            "account_type": "DEMO",
            "open_positions_visible": None,
            **self._safety_flags(),
        }

    def get_open_positions(self) -> dict[str, Any]:
        return self._read_positions()

    def get_open_positions_by_symbol(self, symbol: str) -> dict[str, Any]:
        normalized_symbol = str(symbol or "").strip().upper()
        if not normalized_symbol:
            return {**self._empty_positions("INVALID_SYMBOL", "Symbol is required."), "symbol": normalized_symbol}
        return self._read_positions(symbol=normalized_symbol)

    def sync_journal(self) -> dict[str, Any]:
        position_result = self._read_positions()
        if position_result.get("status") not in {"POSITIONS_FOUND", "NO_OPEN_POSITIONS"}:
            self._latest_sync = {
                **position_result,
                "synced_count": 0,
                "journal_records": [],
                "timestamp": self._timestamp(),
            }
            return self._latest_sync

        journal_records = []
        for position in position_result.get("positions", []):
            journal_records.append(self.persistent_trade_journal_service.record_open_position(self._journal_payload(position)))

        self._latest_sync = {
            "status": "SYNCED" if journal_records else "NO_OPEN_POSITIONS",
            "environment": "DEMO",
            "positions_count": len(position_result.get("positions", [])),
            "synced_count": len(journal_records),
            "journal_records": journal_records,
            "message": "No open MT5 demo positions found." if not journal_records else "Synced MT5 demo open positions into persistent journal.",
            "timestamp": self._timestamp(),
            **self._safety_flags(),
        }
        return self._latest_sync

    def get_latest_sync(self) -> dict[str, Any]:
        return self._latest_sync

    def _read_positions(self, symbol: str | None = None) -> dict[str, Any]:
        if mt5 is None:
            return self._empty_positions("UNAVAILABLE", f"MetaTrader5 package unavailable: {MT5_IMPORT_ERROR}", symbol=symbol)

        initialized = False
        try:
            initialized = bool(mt5.initialize())
            if not initialized:
                return self._empty_positions("NOT_CONNECTED", f"MT5 initialize failed: {mt5.last_error()}", symbol=symbol)

            account = mt5.account_info()
            is_demo = self._is_demo_account(account)
            if not is_demo:
                return self._empty_positions("NON_DEMO_ACCOUNT", "MT5 account is not confirmed as DEMO.", symbol=symbol, account=account)

            raw_positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
            if raw_positions is None:
                raw_positions = []
            positions = [self._normalize_position(position, account) for position in raw_positions]
            return {
                "status": "POSITIONS_FOUND" if positions else "NO_OPEN_POSITIONS",
                "environment": "DEMO",
                "symbol": symbol or "ALL",
                "positions_count": len(positions),
                "positions": positions,
                "empty_state": len(positions) == 0,
                "message": "No open MT5 demo positions found." if not positions else "Open MT5 demo positions read from terminal.",
                "account_login": str(getattr(account, "login", "")) if account else "",
                "server": str(getattr(account, "server", "")) if account else "",
                "timestamp": self._timestamp(),
                **self._safety_flags(),
            }
        except Exception as exc:  # pragma: no cover - depends on terminal state
            return self._empty_positions("READ_FAILED", f"MT5 demo positions read failed: {exc}", symbol=symbol)
        finally:
            if initialized:
                mt5.shutdown()

    def _normalize_position(self, position: Any, account: Any = None) -> dict[str, Any]:
        type_code = getattr(position, "type", None)
        side = {getattr(mt5, "POSITION_TYPE_BUY", 0): "BUY", getattr(mt5, "POSITION_TYPE_SELL", 1): "SELL"}.get(type_code)
        if side is None:
            side = {0: "BUY", 1: "SELL"}.get(type_code, str(type_code) if type_code is not None else "")
        return {
            "ticket": self._number_or_zero(getattr(position, "ticket", 0), int),
            "symbol": str(getattr(position, "symbol", "") or "").upper(),
            "type": side,
            "volume": self._number_or_zero(getattr(position, "volume", 0.0), float),
            "price_open": self._number_or_zero(getattr(position, "price_open", 0.0), float),
            "sl": self._number_or_zero(getattr(position, "sl", 0.0), float),
            "tp": self._number_or_zero(getattr(position, "tp", 0.0), float),
            "price_current": self._number_or_zero(getattr(position, "price_current", 0.0), float),
            "profit": self._number_or_zero(getattr(position, "profit", 0.0), float),
            "time": self._number_or_zero(getattr(position, "time", 0), int),
            "magic": self._number_or_zero(getattr(position, "magic", 0), int),
            "comment": str(getattr(position, "comment", "") or ""),
            "account_login": str(getattr(account, "login", "")) if account else "",
            "server": str(getattr(account, "server", "")) if account else "",
        }

    def _journal_payload(self, position: dict[str, Any]) -> dict[str, Any]:
        return {
            "trade_id": f"mt5_demo_{position['ticket']}",
            "source": "MT5_DEMO",
            "environment": "DEMO",
            "symbol": position["symbol"],
            "side": position["type"],
            "lot": position["volume"],
            "entry_price": position["price_open"],
            "stop_loss": position["sl"],
            "take_profit": position["tp"],
            "profit_loss": position["profit"],
            "mt5_ticket": str(position["ticket"]),
            "mt5_comment": position["comment"],
            "account_login": position["account_login"],
            "server": position["server"],
            "notes": "Synced from MT5 open position.",
        }

    def _is_demo_account(self, account: Any) -> bool:
        if account is None:
            return False
        server = str(getattr(account, "server", "") or "")
        trade_mode = getattr(account, "trade_mode", None)
        demo_mode = getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", None)
        return "demo" in server.lower() or (demo_mode is not None and trade_mode == demo_mode)

    def _empty_positions(self, status: str, message: str, symbol: str | None = None, account: Any = None) -> dict[str, Any]:
        return {
            "status": status,
            "environment": "DEMO",
            "symbol": symbol or "ALL",
            "positions_count": 0,
            "positions": [],
            "empty_state": True,
            "message": message,
            "account_login": str(getattr(account, "login", "")) if account else "",
            "server": str(getattr(account, "server", "")) if account else "",
            "timestamp": self._timestamp(),
            **self._safety_flags(),
        }

    def _empty_sync(self, status: str, message: str) -> dict[str, Any]:
        return {
            "status": status,
            "environment": "DEMO",
            "positions_count": 0,
            "synced_count": 0,
            "journal_records": [],
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

    def _number_or_zero(self, value: Any, number_type: Any) -> Any:
        try:
            return number_type(value)
        except (TypeError, ValueError):
            return number_type(0)

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()
