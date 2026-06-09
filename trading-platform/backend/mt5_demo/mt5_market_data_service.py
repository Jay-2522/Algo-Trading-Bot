from datetime import datetime, timezone
import time
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
            availability = self._symbol_availability(normalized)
            if availability["classification"] in {"SYMBOL_NOT_FOUND", "SYMBOL_HIDDEN"}:
                return self._error_payload(normalized, availability["classification"], availability["message"])
            time.sleep(0.15)
            tick = mt5.symbol_info_tick(normalized)
            info = mt5.symbol_info(normalized)
            recovery = self._recover_tick_quote(normalized, tick, info, availability)
            if recovery["tick_recovery_status"] == "TICK_STILL_UNAVAILABLE":
                return self._stale_tick_payload(normalized, recovery, availability)
            return {
                "symbol": normalized,
                "bid": recovery["bid"],
                "ask": recovery["ask"],
                "spread": recovery["spread"],
                "timestamp": recovery["timestamp"],
                "freshness": "READY",
                "source": recovery["source"],
                "status": "OK",
                "tick_recovery_status": recovery["tick_recovery_status"],
                "simulation_only": True,
                "live_execution_enabled": False,
                "broker_execution_enabled": False,
                "execution_allowed": False,
                "symbol_availability": availability["classification"],
                "symbol_select_result": availability["symbol_select_result"],
                "symbol_select_error": availability["last_error"],
                "mt5_last_error": availability["last_error"],
                "terminal_memory_warning": self._terminal_memory_warning(availability.get("last_error")),
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
            availability = self._symbol_availability(normalized)
            if availability["classification"] in {"SYMBOL_NOT_FOUND", "SYMBOL_HIDDEN"}:
                return self._candle_error_payload(normalized, normalized_timeframe, count, availability["classification"], availability["message"])
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
                "symbol_availability": availability["classification"],
                "symbol_select_result": availability["symbol_select_result"],
                "symbol_select_error": availability["last_error"],
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
            "freshness": tick.get("freshness", "OFFLINE"),
            "source": "MT5_DEMO",
            "status": tick.get("status", "UNAVAILABLE"),
            "error": tick.get("error"),
            "message": tick.get("message"),
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "symbol_availability": tick.get("symbol_availability"),
            "symbol_select_result": tick.get("symbol_select_result"),
            "symbol_select_error": tick.get("symbol_select_error"),
            "tick_recovery_status": tick.get("tick_recovery_status"),
            "mt5_last_error": tick.get("mt5_last_error"),
            "terminal_memory_warning": tick.get("terminal_memory_warning"),
        }

    def get_xauusd_diagnostics(self) -> dict[str, Any]:
        return self.get_symbol_diagnostics("XAUUSD")

    def get_symbol_diagnostics(self, symbol: str) -> dict[str, Any]:
        normalized = self._normalize_symbol(symbol)
        initialized, error = self._initialize()
        if not initialized:
            return {
                "symbol": normalized,
                "initialization_state": "FAILED",
                "initialization_error": error,
                "classification": "MT5_UNAVAILABLE",
                "diagnostic_report": error,
                "simulation_only": True,
                "live_execution_enabled": False,
                "broker_execution_enabled": False,
                "execution_allowed": False,
                "timestamp": self._timestamp(),
            }

        try:
            account = mt5.account_info()
            terminal = mt5.terminal_info()
            info = mt5.symbol_info(normalized)
            tick = mt5.symbol_info_tick(normalized)
            select_result = bool(mt5.symbol_select(normalized, True)) if info is not None else False
            select_error = mt5.last_error()
            symbols_total = self._safe_call(mt5.symbols_total)
            version = self._safe_call(mt5.version)
            availability = self._classify_symbol(normalized, info, select_result, select_error)
            recovery = self._recover_tick_quote(normalized, tick, info, availability)
            if availability["classification"] == "SYMBOL_AVAILABLE" and recovery["tick_recovery_status"] == "TICK_STILL_UNAVAILABLE":
                availability = {
                    **availability,
                    "classification": "SYMBOL_TICK_UNAVAILABLE",
                    "message": f"{normalized} exists but MT5 returned no usable tick or symbol_info bid/ask.",
                }
            report = self._diagnostic_report(normalized, availability, tick, recovery)
            return {
                "symbol": normalized,
                "initialization_state": "INITIALIZED",
                "account_login": str(getattr(account, "login", "")) if account else "",
                "server": str(getattr(account, "server", "")) if account else "",
                "terminal_path": str(getattr(terminal, "path", "")) if terminal else "",
                "terminal_build": getattr(terminal, "build", None) if terminal else None,
                "terminal_symbol_count": symbols_total,
                "mt5_version": version,
                "symbol_info": self._object_to_dict(info),
                "symbol_info_tick": self._object_to_dict(tick),
                "direct_tick_result": recovery["direct_tick_result"],
                "symbol_info_bid": self._positive_float(getattr(info, "bid", None)) if info is not None else None,
                "symbol_info_ask": self._positive_float(getattr(info, "ask", None)) if info is not None else None,
                "symbol_info_last": self._positive_float(getattr(info, "last", None)) if info is not None else None,
                "calculated_spread": recovery["spread"],
                "recovery_status": recovery["tick_recovery_status"],
                "symbol_visibility": bool(getattr(info, "visible", False)) if info is not None else False,
                "symbol_select_result": select_result,
                "mt5_last_error": select_error,
                "terminal_memory_warning": self._terminal_memory_warning(select_error),
                "classification": availability["classification"],
                "diagnostic_report": report,
                "source": "MT5_DEMO",
                "simulation_only": True,
                "live_execution_enabled": False,
                "broker_execution_enabled": False,
                "execution_allowed": False,
                "timestamp": self._timestamp(),
            }
        except Exception as exc:  # pragma: no cover - depends on terminal state
            return {
                "symbol": normalized,
                "initialization_state": "INITIALIZED",
                "classification": "DIAGNOSTICS_FAILED",
                "diagnostic_report": f"MT5 diagnostics failed safely: {exc}",
                "simulation_only": True,
                "live_execution_enabled": False,
                "broker_execution_enabled": False,
                "execution_allowed": False,
                "timestamp": self._timestamp(),
            }
        finally:
            mt5.shutdown()

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
        selected = bool(mt5.symbol_select(symbol, True))
        if not selected:
            return False, f"{symbol} could not be selected in Market Watch: {mt5.last_error()}"
        return True, ""

    def _symbol_availability(self, symbol: str) -> dict[str, Any]:
        info = mt5.symbol_info(symbol)
        select_result = False
        select_error: Any = None
        if info is not None:
            select_result = bool(mt5.symbol_select(symbol, True))
            select_error = mt5.last_error()
        return self._classify_symbol(symbol, info, select_result, select_error)

    def _classify_symbol(self, symbol: str, info: Any, select_result: bool, select_error: Any) -> dict[str, Any]:
        if info is None:
            return {
                "classification": "SYMBOL_NOT_FOUND",
                "message": f"{symbol} was not returned by mt5.symbol_info().",
                "symbol_select_result": False,
                "last_error": select_error,
            }
        visible = bool(getattr(info, "visible", False))
        if visible and not select_result:
            return {
                "classification": "SYMBOL_AVAILABLE_SELECT_FAILED",
                "message": f"{symbol} is visible from mt5.symbol_info(), but mt5.symbol_select() failed: {select_error}",
                "symbol_select_result": False,
                "last_error": select_error,
            }
        if visible:
            return {
                "classification": "SYMBOL_AVAILABLE",
                "message": f"{symbol} is available and visible in MT5.",
                "symbol_select_result": select_result,
                "last_error": select_error,
            }
        if select_result:
            return {
                "classification": "SYMBOL_AVAILABLE",
                "message": f"{symbol} was hidden but mt5.symbol_select() made it available.",
                "symbol_select_result": True,
                "last_error": select_error,
            }
        return {
            "classification": "SYMBOL_HIDDEN",
            "message": f"{symbol} exists but is hidden and mt5.symbol_select() failed: {select_error}",
            "symbol_select_result": False,
            "last_error": select_error,
        }

    def _recover_tick_quote(self, symbol: str, tick: Any, info: Any, availability: dict[str, Any]) -> dict[str, Any]:
        tick_bid = self._positive_float(getattr(tick, "bid", None)) if tick is not None else None
        tick_ask = self._positive_float(getattr(tick, "ask", None)) if tick is not None else None
        tick_time = int(getattr(tick, "time", 0) or 0) if tick is not None else 0
        direct_tick_result = {
            "available": tick is not None,
            "bid": tick_bid,
            "ask": tick_ask,
            "time": tick_time or None,
        }
        if tick_bid is not None and tick_ask is not None and tick_ask > tick_bid:
            return self._quote_recovery_payload(
                symbol,
                tick_bid,
                tick_ask,
                self._epoch_to_iso(tick_time) if tick_time > 0 else self._timestamp(),
                "MT5_SYMBOL_INFO_TICK",
                "TICK_AVAILABLE_DIRECT",
                direct_tick_result,
            )

        info_bid = self._positive_float(getattr(info, "bid", None)) if info is not None else None
        info_ask = self._positive_float(getattr(info, "ask", None)) if info is not None else None
        if info_bid is not None and info_ask is not None and info_ask > info_bid:
            return self._quote_recovery_payload(
                symbol,
                info_bid,
                info_ask,
                self._timestamp(),
                "MT5_SYMBOL_INFO_FIELDS",
                "TICK_AVAILABLE_FROM_SYMBOL_INFO",
                direct_tick_result,
            )

        return {
            "symbol": symbol,
            "bid": tick_bid or info_bid or 0.0,
            "ask": tick_ask or info_ask or 0.0,
            "spread": None,
            "timestamp": None,
            "source": "MT5_DEMO",
            "tick_recovery_status": "TICK_STILL_UNAVAILABLE",
            "direct_tick_result": direct_tick_result,
            "terminal_memory_warning": self._terminal_memory_warning(availability.get("last_error")),
        }

    def _quote_recovery_payload(
        self,
        symbol: str,
        bid: float,
        ask: float,
        timestamp: str,
        source: str,
        recovery_status: str,
        direct_tick_result: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "symbol": symbol,
            "bid": bid,
            "ask": ask,
            "spread": round(ask - bid, 6),
            "timestamp": timestamp,
            "source": source,
            "tick_recovery_status": recovery_status,
            "direct_tick_result": direct_tick_result,
        }

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
            "freshness": "OFFLINE",
            "source": "MT5_DEMO",
            "status": status,
            "error": True,
            "message": message,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
        }

    def _stale_tick_payload(self, symbol: str, recovery: dict[str, Any], availability: dict[str, Any] | None = None) -> dict[str, Any]:
        availability = availability or {}
        return {
            "symbol": symbol,
            "bid": recovery.get("bid") or 0.0,
            "ask": recovery.get("ask") or 0.0,
            "spread": recovery.get("spread"),
            "timestamp": recovery.get("timestamp"),
            "freshness": "OFFLINE",
            "source": "MT5_DEMO",
            "status": "SYMBOL_TICK_UNAVAILABLE",
            "error": "STALE_TICK",
            "message": self._tick_unavailable_message(symbol, availability, "SYMBOL_TICK_UNAVAILABLE"),
            "tick_recovery_status": "TICK_STILL_UNAVAILABLE",
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "symbol_availability": availability.get("classification"),
            "symbol_select_result": availability.get("symbol_select_result"),
            "symbol_select_error": availability.get("last_error"),
            "mt5_last_error": availability.get("last_error"),
            "terminal_memory_warning": self._terminal_memory_warning(availability.get("last_error")),
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

    def _object_to_dict(self, value: Any) -> dict[str, Any] | None:
        if value is None:
            return None
        if hasattr(value, "_asdict"):
            return dict(value._asdict())
        keys = [key for key in dir(value) if not key.startswith("_")]
        result: dict[str, Any] = {}
        for key in keys:
            item = getattr(value, key, None)
            if isinstance(item, (str, int, float, bool)) or item is None:
                result[key] = item
        return result

    def _safe_call(self, fn: Any) -> Any:
        try:
            return fn()
        except Exception as exc:  # pragma: no cover - diagnostic only
            return f"UNAVAILABLE: {exc}"

    def _diagnostic_report(self, symbol: str, availability: dict[str, Any], tick: Any, recovery: dict[str, Any] | None = None) -> str:
        classification = availability.get("classification")
        recovery_status = (recovery or {}).get("tick_recovery_status")
        if recovery_status == "TICK_AVAILABLE_DIRECT":
            return f"{symbol} live quote recovered directly from mt5.symbol_info_tick()."
        if recovery_status == "TICK_AVAILABLE_FROM_SYMBOL_INFO":
            return f"{symbol} live quote recovered from mt5.symbol_info() bid/ask fields without relying on symbol_select()."
        if classification == "SYMBOL_AVAILABLE_SELECT_FAILED":
            return (
                f"{symbol} is available because mt5.symbol_info() returned a visible symbol. "
                f"mt5.symbol_select() failed with {availability.get('last_error')}, so selection failure is recorded as a terminal/API warning, "
                "not as symbol unavailability."
            )
        if classification == "SYMBOL_TICK_UNAVAILABLE":
            return f"{symbol} exists, but mt5.symbol_info_tick() returned no tick; validation cannot report a live price."
        if classification == "SYMBOL_AVAILABLE":
            tick_text = "and tick data is available" if tick is not None else "but tick data is unavailable"
            return f"{symbol} is available from mt5.symbol_info() {tick_text}."
        return str(availability.get("message") or f"{symbol} diagnostic classification: {classification}")

    def _tick_unavailable_message(self, symbol: str, availability: dict[str, Any], status: str) -> str:
        prefix = str(availability.get("message") or f"{symbol} is available from mt5.symbol_info().")
        if status == "SYMBOL_TICK_UNAVAILABLE":
            return f"{prefix} MT5 did not provide a usable tick."
        return f"{prefix} MT5 tick is stale. Market may be closed or broker feed is not updating."

    def _positive_float(self, value: Any) -> float | None:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if number > 0 else None

    def _terminal_memory_warning(self, error: Any) -> bool:
        text = str(error).lower()
        return "out of memory" in text or text.startswith("(-3") or text.startswith("[-3")

    def _tick_freshness(self, timestamp: str | None) -> str:
        if not timestamp:
            return "OFFLINE"
        try:
            parsed = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00")).astimezone(timezone.utc)
        except ValueError:
            return "OFFLINE"
        age_seconds = (datetime.now(timezone.utc) - parsed).total_seconds()
        if age_seconds <= 5 * 60:
            return "READY"
        if age_seconds <= 30 * 60:
            return "STALE"
        return "OFFLINE"
