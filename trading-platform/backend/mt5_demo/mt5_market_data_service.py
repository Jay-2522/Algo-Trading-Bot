from datetime import datetime, timezone
import os
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
    stale_grace_seconds = 10
    failed_tick_threshold = 3

    def __init__(self) -> None:
        self._last_good_ticks: dict[str, dict[str, Any]] = {}
        self._failed_tick_reads: dict[str, int] = {}

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
            return self._temporary_tick_failure_payload(normalized, "MT5_UNAVAILABLE", error)

        try:
            account = mt5.account_info()
            source = self._source_from_account(account)
            availability = self._symbol_availability(normalized)
            if availability["classification"] in {"SYMBOL_NOT_FOUND", "SYMBOL_HIDDEN"}:
                return self._error_payload(normalized, availability["classification"], availability["message"])
            time.sleep(0.15)
            tick = mt5.symbol_info_tick(normalized)
            info = mt5.symbol_info(normalized)
            recovery = self._recover_tick_quote(normalized, tick, info, availability)
            if recovery["tick_recovery_status"] == "TICK_STILL_UNAVAILABLE":
                return self._temporary_tick_failure_payload(
                    normalized,
                    "SYMBOL_TICK_UNAVAILABLE",
                    self._tick_unavailable_message(normalized, availability, "SYMBOL_TICK_UNAVAILABLE"),
                    recovery,
                    availability,
                    source,
                )
            payload = {
                "symbol": normalized,
                "bid": recovery["bid"],
                "ask": recovery["ask"],
                "spread": recovery["spread"],
                "timestamp": recovery["timestamp"],
                "freshness": "READY",
                "source": source,
                "quote_source": recovery["source"],
                "status": "OK",
                "market_status": "MARKET_READY",
                "stale": False,
                "consecutive_failed_tick_reads": 0,
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
            self._record_successful_tick(normalized, payload)
            return payload
        except Exception as exc:  # pragma: no cover - depends on terminal state
            return self._temporary_tick_failure_payload(normalized, "TICK_READ_FAILED", str(exc))
        finally:
            mt5.shutdown()

    def get_symbol_candles(self, symbol: str, timeframe: str, count: int = 50) -> dict[str, Any]:
        normalized = self._normalize_symbol(symbol)
        normalized_timeframe = self._normalize_timeframe(timeframe)
        count = max(1, min(int(count or 50), 1000))

        if normalized not in self.supported_symbols:
            return self._candle_error_payload(normalized, normalized_timeframe, count, "INVALID_SYMBOL", f"Unsupported symbol: {symbol}")
        if normalized_timeframe not in self.supported_timeframes:
            return self._candle_error_payload(normalized, normalized_timeframe, count, "INVALID_TIMEFRAME", f"Unsupported timeframe: {timeframe}")

        initialized, error = self._initialize()
        if not initialized:
            return self._candle_error_payload(normalized, normalized_timeframe, count, "MT5_UNAVAILABLE", error)

        try:
            account = mt5.account_info()
            source = self._source_from_account(account)
            account_type = self._account_type(account)
            resolution = self._resolve_market_watch_symbol(normalized)
            resolved_symbol = str(resolution.get("resolved_symbol") or normalized)
            if not resolution.get("resolved"):
                return self._candle_error_payload(
                    normalized,
                    normalized_timeframe,
                    count,
                    "SYMBOL_NOT_FOUND",
                    str(resolution.get("message") or f"{normalized} could not be resolved in MT5 Market Watch."),
                    resolution=resolution,
                )
            select_result = bool(mt5.symbol_select(resolved_symbol, True))
            select_error = mt5.last_error()
            availability = self._symbol_availability(resolved_symbol)
            if availability["classification"] in {"SYMBOL_NOT_FOUND", "SYMBOL_HIDDEN"}:
                return self._candle_error_payload(
                    normalized,
                    normalized_timeframe,
                    count,
                    availability["classification"],
                    availability["message"],
                    resolution={**resolution, "symbol_select_result": select_result, "last_error": select_error},
                )
            mt5_timeframe = self._mt5_timeframe(normalized_timeframe)
            rates = mt5.copy_rates_from_pos(resolved_symbol, mt5_timeframe, 0, count)
            last_error = mt5.last_error()
            if rates is None or len(rates) == 0:
                return self._candle_error_payload(
                    normalized,
                    normalized_timeframe,
                    count,
                    "CANDLES_UNAVAILABLE",
                    f"No candles returned for {normalized} resolved as {resolved_symbol} {normalized_timeframe}: {last_error}",
                    resolution={**resolution, "symbol_select_result": select_result, "last_error": last_error},
                )
            candles = [self._rate_to_candle(rate) for rate in rates]
            return {
                "symbol": normalized,
                "requested_symbol": normalized,
                "resolved_symbol": resolved_symbol,
                "timeframe": normalized_timeframe,
                "count": len(candles),
                "requested_count": count,
                "returned_count": len(candles),
                "candles": candles,
                "source": source,
                "broker_source": source,
                "account_login": str(getattr(account, "login", "")) if account else "",
                "server": str(getattr(account, "server", "")) if account else "",
                "account_type": account_type,
                **self._connection_diagnostics(account),
                "status": "OK",
                "simulation_only": True,
                "live_execution_enabled": False,
                "broker_execution_enabled": False,
                "execution_allowed": False,
                "symbol_availability": availability["classification"],
                "symbol_select_result": select_result,
                "symbol_select_error": select_error,
                "mt5_last_error": last_error,
                "symbol_resolution": resolution,
                "timestamp": self._timestamp(),
            }
        except Exception as exc:  # pragma: no cover - depends on terminal state
            return self._candle_error_payload(normalized, normalized_timeframe, count, "CANDLE_READ_FAILED", str(exc))
        finally:
            pass

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
            "market_status": tick.get("market_status"),
            "stale": tick.get("stale", False),
            "consecutive_failed_tick_reads": tick.get("consecutive_failed_tick_reads", 0),
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
            source = self._source_from_account(account)
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
                "account_type": self._account_type(account),
                "broker_detected": "VANTAGE_DEMO" if source == "VANTAGE_DEMO" else None,
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
                "tick_available": recovery["tick_recovery_status"] in {"TICK_AVAILABLE_DIRECT", "TICK_AVAILABLE_FROM_SYMBOL_INFO"},
                "bid": recovery["bid"] if recovery["tick_recovery_status"] != "TICK_STILL_UNAVAILABLE" else None,
                "ask": recovery["ask"] if recovery["tick_recovery_status"] != "TICK_STILL_UNAVAILABLE" else None,
                "spread": recovery["spread"],
                "source": source,
                "readiness_result": "READY" if recovery["tick_recovery_status"] in {"TICK_AVAILABLE_DIRECT", "TICK_AVAILABLE_FROM_SYMBOL_INFO"} else "BLOCKED",
                "symbol_visibility": bool(getattr(info, "visible", False)) if info is not None else False,
                "symbol_select_result": select_result,
                "mt5_last_error": select_error,
                "terminal_memory_warning": self._terminal_memory_warning(select_error),
                "classification": availability["classification"],
                "diagnostic_report": report,
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

    def _connection_diagnostics(self, account: Any = None) -> dict[str, Any]:
        terminal = None
        try:
            terminal = mt5.terminal_info() if mt5 is not None else None
        except Exception:
            terminal = None
        return {
            "process_id": os.getpid(),
            "connection_id": "|".join(
                [
                    f"pid:{os.getpid()}",
                    f"login:{getattr(account, 'login', '') if account else ''}",
                    f"server:{getattr(account, 'server', '') if account else ''}",
                    f"terminal:{getattr(terminal, 'path', '') if terminal else ''}",
                ]
            ),
            "terminal_path": str(getattr(terminal, "path", "")) if terminal else "",
        }

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

    def _resolve_market_watch_symbol(self, symbol: str) -> dict[str, Any]:
        requested = self._normalize_symbol(symbol)
        candidates: list[str] = []
        for candidate in [symbol, requested, requested.lower(), requested.capitalize()]:
            candidate_text = str(candidate or "").strip()
            if candidate_text and candidate_text not in candidates:
                candidates.append(candidate_text)
        discovered = self._matching_market_watch_symbols(requested)
        for candidate in discovered:
            if candidate not in candidates:
                candidates.append(candidate)

        attempts: list[dict[str, Any]] = []
        for candidate in candidates:
            info = mt5.symbol_info(candidate)
            select_result = bool(mt5.symbol_select(candidate, True)) if info is not None else False
            last_error = mt5.last_error()
            attempts.append(
                {
                    "symbol": candidate,
                    "symbol_info_found": info is not None,
                    "visible": bool(getattr(info, "visible", False)) if info is not None else False,
                    "symbol_select_result": select_result,
                    "last_error": last_error,
                }
            )
            if info is not None and (select_result or bool(getattr(info, "visible", False))):
                return {
                    "requested_symbol": requested,
                    "resolved_symbol": candidate,
                    "resolved": True,
                    "resolution_method": "MARKET_WATCH_SYMBOL",
                    "attempts": attempts,
                    "last_error": last_error,
                }
        return {
            "requested_symbol": requested,
            "resolved_symbol": requested,
            "resolved": False,
            "resolution_method": "UNRESOLVED",
            "attempts": attempts,
            "last_error": attempts[-1]["last_error"] if attempts else None,
            "message": f"{requested} was not found in MT5 Market Watch or available broker symbols.",
        }

    def _matching_market_watch_symbols(self, requested: str) -> list[str]:
        try:
            symbols = mt5.symbols_get() or []
        except Exception:
            return []
        requested_key = self._symbol_key(requested)
        exact: list[str] = []
        prefixed_or_suffixed: list[str] = []
        contains: list[str] = []
        for item in symbols:
            name = str(getattr(item, "name", "") or "")
            if not name:
                continue
            key = self._symbol_key(name)
            if key == requested_key:
                exact.append(name)
            elif key.startswith(requested_key) or key.endswith(requested_key):
                prefixed_or_suffixed.append(name)
            elif requested_key in key:
                contains.append(name)
        return self._dedupe_symbols(exact + prefixed_or_suffixed + contains)[:20]

    def _symbol_key(self, symbol: str) -> str:
        return "".join(ch for ch in str(symbol or "").upper() if ch.isalnum())

    def _dedupe_symbols(self, symbols: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for symbol in symbols:
            if symbol in seen:
                continue
            seen.add(symbol)
            result.append(symbol)
        return result

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
            "market_status": status if status in {"SYMBOL_TICK_UNAVAILABLE", "FEED_OFFLINE", "MARKET_CLOSED"} else "SYMBOL_TICK_UNAVAILABLE",
            "stale": False,
            "consecutive_failed_tick_reads": self._failed_tick_reads.get(symbol, 0),
            "error": True,
            "message": message,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
        }

    def _temporary_tick_failure_payload(
        self,
        symbol: str,
        status: str,
        message: str,
        recovery: dict[str, Any] | None = None,
        availability: dict[str, Any] | None = None,
        source: str = "MT5_DEMO",
    ) -> dict[str, Any]:
        failures = self._failed_tick_reads.get(symbol, 0) + 1
        self._failed_tick_reads[symbol] = failures
        cached = self._last_good_ticks.get(symbol)
        age = self._tick_age_seconds(cached)
        if cached and failures < self.failed_tick_threshold and age <= self.stale_grace_seconds:
            payload = dict(cached)
            payload.update(
                {
                    "freshness": "STALE",
                    "status": "STALE_TICK",
                    "market_status": "STALE_TICK",
                    "stale": True,
                    "stale_age_seconds": round(age, 2),
                    "consecutive_failed_tick_reads": failures,
                    "error": "STALE_TICK",
                    "message": message,
                    "last_successful_tick_at": cached.get("timestamp"),
                    "tick_recovery_status": (recovery or {}).get("tick_recovery_status", "TICK_STILL_UNAVAILABLE"),
                    "symbol_availability": (availability or {}).get("classification", cached.get("symbol_availability")),
                    "symbol_select_result": (availability or {}).get("symbol_select_result", cached.get("symbol_select_result")),
                    "symbol_select_error": (availability or {}).get("last_error", cached.get("symbol_select_error")),
                    "mt5_last_error": (availability or {}).get("last_error", cached.get("mt5_last_error")),
                }
            )
            return payload
        offline_status = "FEED_OFFLINE" if cached else "SYMBOL_TICK_UNAVAILABLE"
        payload = self._stale_tick_payload(symbol, recovery or {}, availability, source)
        payload.update(
            {
                "status": offline_status,
                "market_status": offline_status,
                "freshness": "OFFLINE",
                "stale": bool(cached),
                "stale_age_seconds": round(age, 2) if cached else None,
                "consecutive_failed_tick_reads": failures,
                "message": message,
            }
        )
        if cached:
            payload["bid"] = cached.get("bid")
            payload["ask"] = cached.get("ask")
            payload["spread"] = cached.get("spread")
            payload["last_successful_tick_at"] = cached.get("timestamp")
        return payload

    def _stale_tick_payload(
        self,
        symbol: str,
        recovery: dict[str, Any],
        availability: dict[str, Any] | None = None,
        source: str = "MT5_DEMO",
    ) -> dict[str, Any]:
        availability = availability or {}
        return {
            "symbol": symbol,
            "bid": recovery.get("bid") or 0.0,
            "ask": recovery.get("ask") or 0.0,
            "spread": recovery.get("spread"),
            "timestamp": recovery.get("timestamp"),
            "freshness": "OFFLINE",
            "source": source,
            "status": "SYMBOL_TICK_UNAVAILABLE",
            "market_status": "SYMBOL_TICK_UNAVAILABLE",
            "stale": False,
            "consecutive_failed_tick_reads": self._failed_tick_reads.get(symbol, 0),
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

    def _record_successful_tick(self, symbol: str, payload: dict[str, Any]) -> None:
        self._failed_tick_reads[symbol] = 0
        self._last_good_ticks[symbol] = dict(payload)

    def _tick_age_seconds(self, tick: dict[str, Any] | None) -> float:
        if not tick:
            return float("inf")
        try:
            timestamp = datetime.fromisoformat(str(tick.get("timestamp")).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return float("inf")
        return max(0.0, (datetime.now(timezone.utc) - timestamp).total_seconds())

    def _candle_error_payload(self, symbol: str, timeframe: str, count: int, status: str, message: str, resolution: dict[str, Any] | None = None) -> dict[str, Any]:
        resolution = resolution or {}
        return {
            "symbol": symbol,
            "requested_symbol": resolution.get("requested_symbol", symbol),
            "resolved_symbol": resolution.get("resolved_symbol", symbol),
            "timeframe": timeframe,
            "count": 0,
            "requested_count": count,
            "returned_count": 0,
            "candles": [],
            "source": "MT5_DEMO",
            "status": status,
            "error": True,
            "message": message,
            "symbol_select_result": resolution.get("symbol_select_result"),
            "symbol_select_error": resolution.get("last_error"),
            "mt5_last_error": resolution.get("last_error"),
            "symbol_resolution": resolution,
            **self._connection_diagnostics(),
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

    def _source_from_account(self, account: Any) -> str:
        server = str(getattr(account, "server", "") if account else "")
        if "vantage" in server.lower() and self._account_type(account) == "DEMO":
            return "VANTAGE_DEMO"
        return "MT5_DEMO"

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
