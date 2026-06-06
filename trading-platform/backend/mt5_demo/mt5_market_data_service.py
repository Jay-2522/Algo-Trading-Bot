from datetime import datetime, timezone
from typing import Any


try:
    import MetaTrader5 as mt5
except Exception as exc:  # pragma: no cover - depends on local MT5 installation
    mt5 = None
    MT5_IMPORT_ERROR = exc
else:
    MT5_IMPORT_ERROR = None


class MT5MarketDataService:
    """Read-only MT5 demo market-data retrieval for Phase 15."""

    supported_symbols = {"EURUSD", "XAUUSD"}
    supported_timeframes = {"M1", "M5", "M15", "H1", "H4", "D1"}

    def get_market_data_status(self) -> dict[str, Any]:
        state = self._read_connection_state()
        return {
            "environment": "DEMO",
            "source": "MT5_DEMO",
            "status": "READY" if state["terminal_running"] else "UNAVAILABLE",
            "mt5_installed": state["mt5_installed"],
            "terminal_running": state["terminal_running"],
            "account_connected": state["account_connected"],
            "account_type": state["account_type"],
            "supported_symbols": sorted(self.supported_symbols),
            "supported_timeframes": sorted(self.supported_timeframes),
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "warnings": state["warnings"],
            "timestamp": self._timestamp(),
        }

    def get_symbol_tick(self, symbol: str) -> dict[str, Any]:
        normalized = self._normalize_symbol(symbol)
        if normalized not in self.supported_symbols:
            return self._error_payload(normalized, "INVALID_SYMBOL", f"Unsupported symbol: {symbol}")

        initialized, error = self._initialize()
        if not initialized:
            return self._error_payload(normalized, "MT5_UNAVAILABLE", error)

        try:
            visible, visibility_error = self._ensure_symbol_visible(normalized)
            if not visible:
                return self._error_payload(normalized, "SYMBOL_UNAVAILABLE", visibility_error)
            tick = mt5.symbol_info_tick(normalized)
            if tick is None:
                return self._error_payload(normalized, "TICK_UNAVAILABLE", f"No tick returned for {normalized}: {mt5.last_error()}")
            bid = float(getattr(tick, "bid", 0.0) or 0.0)
            ask = float(getattr(tick, "ask", 0.0) or 0.0)
            raw_timestamp = int(getattr(tick, "time", 0) or 0)
            if bid <= 0 or ask <= 0 or raw_timestamp <= 0:
                return self._stale_tick_payload(normalized, bid, ask, raw_timestamp)
            spread = round(ask - bid, 6)
            timestamp = self._epoch_to_iso(raw_timestamp)
            return {
                "symbol": normalized,
                "bid": bid,
                "ask": ask,
                "spread": spread,
                "timestamp": timestamp,
                "source": "MT5_DEMO",
                "status": "OK",
                "simulation_only": True,
                "live_execution_enabled": False,
                "broker_execution_enabled": False,
                "execution_allowed": False,
            }
        except Exception as exc:  # pragma: no cover - depends on terminal state
            return self._error_payload(normalized, "TICK_READ_FAILED", str(exc))
        finally:
            mt5.shutdown()

    def get_symbol_candles(self, symbol: str, timeframe: str, count: int = 50) -> dict[str, Any]:
        normalized = self._normalize_symbol(symbol)
        normalized_timeframe = self._normalize_timeframe(timeframe)
        count = max(1, min(int(count or 50), 500))

        if normalized not in self.supported_symbols:
            return self._candle_error_payload(normalized, normalized_timeframe, count, "INVALID_SYMBOL", f"Unsupported symbol: {symbol}")
        if normalized_timeframe not in self.supported_timeframes:
            return self._candle_error_payload(normalized, normalized_timeframe, count, "INVALID_TIMEFRAME", f"Unsupported timeframe: {timeframe}")

        initialized, error = self._initialize()
        if not initialized:
            return self._candle_error_payload(normalized, normalized_timeframe, count, "MT5_UNAVAILABLE", error)

        try:
            visible, visibility_error = self._ensure_symbol_visible(normalized)
            if not visible:
                return self._candle_error_payload(normalized, normalized_timeframe, count, "SYMBOL_UNAVAILABLE", visibility_error)
            mt5_timeframe = self._mt5_timeframe(normalized_timeframe)
            rates = mt5.copy_rates_from_pos(normalized, mt5_timeframe, 0, count)
            if rates is None or len(rates) == 0:
                return self._candle_error_payload(
                    normalized,
                    normalized_timeframe,
                    count,
                    "CANDLES_UNAVAILABLE",
                    f"No candles returned for {normalized} {normalized_timeframe}: {mt5.last_error()}",
                )
            candles = [self._rate_to_candle(rate) for rate in rates]
            return {
                "symbol": normalized,
                "timeframe": normalized_timeframe,
                "count": len(candles),
                "requested_count": count,
                "candles": candles,
                "source": "MT5_DEMO",
                "status": "OK",
                "simulation_only": True,
                "live_execution_enabled": False,
                "broker_execution_enabled": False,
                "execution_allowed": False,
                "timestamp": self._timestamp(),
            }
        except Exception as exc:  # pragma: no cover - depends on terminal state
            return self._candle_error_payload(normalized, normalized_timeframe, count, "CANDLE_READ_FAILED", str(exc))
        finally:
            mt5.shutdown()

    def get_symbol_spread(self, symbol: str) -> dict[str, Any]:
        tick = self.get_symbol_tick(symbol)
        return {
            "symbol": tick.get("symbol", self._normalize_symbol(symbol)),
            "bid": tick.get("bid"),
            "ask": tick.get("ask"),
            "spread": tick.get("spread"),
            "timestamp": tick.get("timestamp", self._timestamp()),
            "source": "MT5_DEMO",
            "status": tick.get("status", "UNAVAILABLE"),
            "error": tick.get("error"),
            "message": tick.get("message"),
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
        }

    def _initialize(self) -> tuple[bool, str]:
        if mt5 is None:
            return False, f"MetaTrader5 Python package is unavailable: {MT5_IMPORT_ERROR}"
        try:
            initialized = bool(mt5.initialize())
            if not initialized:
                return False, f"MT5 initialize failed: {mt5.last_error()}"
            return True, ""
        except Exception as exc:  # pragma: no cover - depends on terminal state
            return False, f"MT5 initialize raised an exception: {exc}"

    def _read_connection_state(self) -> dict[str, Any]:
        warnings: list[str] = []
        initialized, error = self._initialize()
        if not initialized:
            return {
                "mt5_installed": mt5 is not None,
                "terminal_running": False,
                "account_connected": False,
                "account_type": "DEMO",
                "warnings": [error],
            }
        try:
            account = mt5.account_info()
            account_type = self._account_type(account)
            if account is None:
                warnings.append(f"MT5 account info unavailable: {mt5.last_error()}")
            if account is not None and account_type != "DEMO":
                warnings.append("Connected MT5 account is not identified as DEMO; read-only market data remains safe.")
            return {
                "mt5_installed": True,
                "terminal_running": True,
                "account_connected": account is not None and account_type == "DEMO",
                "account_type": account_type,
                "warnings": warnings,
            }
        except Exception as exc:  # pragma: no cover - depends on terminal state
            return {
                "mt5_installed": True,
                "terminal_running": True,
                "account_connected": False,
                "account_type": "DEMO",
                "warnings": [f"MT5 account status read failed: {exc}"],
            }
        finally:
            mt5.shutdown()

    def _ensure_symbol_visible(self, symbol: str) -> tuple[bool, str]:
        info = mt5.symbol_info(symbol)
        if info is None:
            return False, f"{symbol} is unavailable in MT5."
        if not getattr(info, "visible", False):
            selected = bool(mt5.symbol_select(symbol, True))
            if not selected:
                return False, f"{symbol} could not be selected in Market Watch: {mt5.last_error()}"
        return True, ""

    def _mt5_timeframe(self, timeframe: str) -> Any:
        return {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1,
        }[timeframe]

    def _rate_to_candle(self, rate: Any) -> dict[str, Any]:
        return {
            "time": self._epoch_to_iso(rate["time"]),
            "open": float(rate["open"]),
            "high": float(rate["high"]),
            "low": float(rate["low"]),
            "close": float(rate["close"]),
            "tick_volume": int(rate["tick_volume"]),
        }

    def _error_payload(self, symbol: str, status: str, message: str) -> dict[str, Any]:
        return {
            "symbol": symbol,
            "bid": None,
            "ask": None,
            "spread": None,
            "timestamp": self._timestamp(),
            "source": "MT5_DEMO",
            "status": status,
            "error": True,
            "message": message,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
        }

    def _stale_tick_payload(self, symbol: str, bid: float, ask: float, raw_timestamp: int) -> dict[str, Any]:
        return {
            "symbol": symbol,
            "bid": bid,
            "ask": ask,
            "spread": round(ask - bid, 6) if bid > 0 and ask > 0 else None,
            "timestamp": self._epoch_to_iso(raw_timestamp) if raw_timestamp > 0 else None,
            "source": "MT5_DEMO",
            "status": "STALE_OR_UNAVAILABLE",
            "error": "INVALID_TICK_DATA",
            "message": f"No valid live tick available for {symbol} from MT5 demo feed.",
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
        }

    def _candle_error_payload(self, symbol: str, timeframe: str, count: int, status: str, message: str) -> dict[str, Any]:
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "count": 0,
            "requested_count": count,
            "candles": [],
            "source": "MT5_DEMO",
            "status": status,
            "error": True,
            "message": message,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }

    def _normalize_symbol(self, symbol: str) -> str:
        return str(symbol or "").strip().upper()

    def _normalize_timeframe(self, timeframe: str) -> str:
        return str(timeframe or "").strip().upper()

    def _account_type(self, account: Any) -> str:
        if account is None or mt5 is None:
            return "DEMO"
        trade_mode = getattr(account, "trade_mode", None)
        demo_mode = getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", 0)
        return "DEMO" if trade_mode == demo_mode else "NON_DEMO"

    def _epoch_to_iso(self, value: Any) -> str:
        if value is None:
            return self._timestamp()
        return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat()

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()
