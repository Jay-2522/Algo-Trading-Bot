from datetime import datetime, timezone
from typing import Any


try:
    import MetaTrader5 as mt5
except Exception as exc:  # pragma: no cover - depends on local MT5 installation
    mt5 = None
    MT5_IMPORT_ERROR = exc
else:
    MT5_IMPORT_ERROR = None


class MT5DemoService:
    """Read-only MT5 demo connectivity checks for Phase 14."""

    symbols = ["XAUUSD", "EURUSD"]

    def get_status(self) -> dict:
        state = self._read_state()
        return {
            "environment": "DEMO",
            "mt5_installed": state["mt5_installed"],
            "terminal_running": state["terminal_running"],
            "account_connected": state["account_connected"],
            "account_type": state["account_type"],
            "login": state["login"],
            "server": state["server"],
            "balance": state["balance"],
            "equity": state["equity"],
            "connected_symbols": state["connected_symbols"],
            "status": "CONNECTED" if state["account_connected"] else "NOT_CONNECTED",
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
            "warnings": state["warnings"],
        }

    def get_account(self) -> dict:
        status = self.get_status()
        return {
            "environment": "DEMO",
            "account_connected": status["account_connected"],
            "account_type": status["account_type"],
            "login": status["login"],
            "server": status["server"],
            "balance": status["balance"],
            "equity": status["equity"],
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "warnings": status["warnings"],
            "timestamp": self._timestamp(),
        }

    def get_symbols(self) -> dict:
        state = self._read_state()
        return {
            "environment": "DEMO",
            "symbols": state["symbol_checks"],
            "connected_symbols": state["connected_symbols"],
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }

    def get_health(self) -> dict:
        status = self.get_status()
        return {
            "environment": "DEMO",
            "status": status["status"],
            "healthy": status["mt5_installed"] and status["terminal_running"],
            "mt5_installed": status["mt5_installed"],
            "terminal_running": status["terminal_running"],
            "account_connected": status["account_connected"],
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "warnings": status["warnings"],
            "timestamp": self._timestamp(),
        }

    def get_market_watch(self) -> dict:
        state = self._read_state()
        return {
            "environment": "DEMO",
            "symbols": state["symbol_checks"],
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }

    def block_execution_attempt(self, action: str) -> dict:
        return {
            "action": action,
            "allowed": False,
            "reason": "PHASE_14_DEMO_ONLY",
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }

    def _read_state(self) -> dict:
        warnings: list[str] = []
        if mt5 is None:
            return self._empty_state(
                warnings=[
                    "MetaTrader5 Python package is unavailable.",
                    f"Import error: {MT5_IMPORT_ERROR}",
                ]
            )

        initialized = False
        try:
            initialized = bool(mt5.initialize())
            if not initialized:
                warnings.append(f"MT5 initialize failed: {mt5.last_error()}")
                return self._empty_state(mt5_installed=True, warnings=warnings)

            account = mt5.account_info()
            account_connected = account is not None
            if not account_connected:
                warnings.append(f"MT5 account info unavailable: {mt5.last_error()}")

            symbol_checks = [self._symbol_snapshot(symbol) for symbol in self.symbols]
            connected_symbols = [item["symbol"] for item in symbol_checks if item["exists"]]
            account_type = self._account_type(account)
            if account_connected and account_type != "DEMO":
                warnings.append("Connected MT5 account is not identified as DEMO; execution remains blocked.")

            return {
                "mt5_installed": True,
                "terminal_running": True,
                "account_connected": account_connected and account_type == "DEMO",
                "account_type": account_type,
                "login": str(getattr(account, "login", "")) if account else "",
                "server": str(getattr(account, "server", "")) if account else "",
                "balance": str(getattr(account, "balance", "")) if account else "",
                "equity": str(getattr(account, "equity", "")) if account else "",
                "connected_symbols": connected_symbols,
                "symbol_checks": symbol_checks,
                "warnings": warnings,
            }
        except Exception as exc:  # pragma: no cover - depends on terminal state
            warnings.append(f"MT5 demo status read failed: {exc}")
            return self._empty_state(mt5_installed=True, terminal_running=initialized, warnings=warnings)
        finally:
            if initialized:
                mt5.shutdown()

    def _empty_state(
        self,
        mt5_installed: bool = False,
        terminal_running: bool = False,
        warnings: list[str] | None = None,
    ) -> dict:
        return {
            "mt5_installed": mt5_installed,
            "terminal_running": terminal_running,
            "account_connected": False,
            "account_type": "DEMO",
            "login": "",
            "server": "",
            "balance": "",
            "equity": "",
            "connected_symbols": [],
            "symbol_checks": [self._unavailable_symbol(symbol) for symbol in self.symbols],
            "warnings": warnings or [],
        }

    def _symbol_snapshot(self, symbol: str) -> dict:
        info = mt5.symbol_info(symbol)
        if info is None:
            return self._unavailable_symbol(symbol)
        if not getattr(info, "visible", False):
            mt5.symbol_select(symbol, True)
            info = mt5.symbol_info(symbol) or info
        tick = mt5.symbol_info_tick(symbol)
        bid = float(getattr(tick, "bid", 0.0) or 0.0) if tick else None
        ask = float(getattr(tick, "ask", 0.0) or 0.0) if tick else None
        spread = round(ask - bid, 6) if bid is not None and ask is not None else None
        return {
            "symbol": symbol,
            "exists": True,
            "visible": bool(getattr(info, "visible", False)),
            "bid": bid,
            "ask": ask,
            "spread": spread,
            "trade_allowed": False,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
        }

    def _unavailable_symbol(self, symbol: str) -> dict:
        return {
            "symbol": symbol,
            "exists": False,
            "visible": False,
            "bid": None,
            "ask": None,
            "spread": None,
            "trade_allowed": False,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
        }

    def _account_type(self, account: Any) -> str:
        if account is None:
            return "DEMO"
        trade_mode = getattr(account, "trade_mode", None)
        demo_mode = getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", 0)
        return "DEMO" if trade_mode == demo_mode else "NON_DEMO"

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()
