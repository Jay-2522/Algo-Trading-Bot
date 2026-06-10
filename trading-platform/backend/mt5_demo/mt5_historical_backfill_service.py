from datetime import datetime, timezone
from typing import Any

from backend.mt5_demo.mt5_market_data_service import MT5MarketDataService


class MT5HistoricalBackfillService:
    """Read-only MT5 demo historical candle backfill."""

    supported_symbols = {"EURUSD", "XAUUSD"}
    supported_timeframes = {"M5", "M15", "H1", "H4", "D1"}
    timeframe_seconds = {
        "M5": 5 * 60,
        "M15": 15 * 60,
        "H1": 60 * 60,
        "H4": 4 * 60 * 60,
        "D1": 24 * 60 * 60,
    }

    def __init__(self, market_data_service: MT5MarketDataService | None = None) -> None:
        self.market_data_service = market_data_service or MT5MarketDataService()

    def get_status(self) -> dict[str, Any]:
        return {
            "status": "HISTORICAL_BACKFILL_READY",
            "source": "MT5_DEMO",
            "supported_symbols": sorted(self.supported_symbols),
            "supported_timeframes": sorted(self.supported_timeframes),
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }

    def fetch_history(self, symbol: str, timeframe: str, count: int = 500) -> dict[str, Any]:
        normalized_symbol = self._normalize_symbol(symbol)
        normalized_timeframe = self._normalize_timeframe(timeframe)
        count = max(1, min(int(count or 500), 1000))
        if normalized_symbol not in self.supported_symbols:
            return self._error_payload(normalized_symbol, normalized_timeframe, count, "INVALID_SYMBOL", f"Unsupported symbol: {symbol}")
        if normalized_timeframe not in self.supported_timeframes:
            return self._error_payload(normalized_symbol, normalized_timeframe, count, "INVALID_TIMEFRAME", f"Unsupported timeframe: {timeframe}")

        raw_payload = self.market_data_service.get_symbol_candles(normalized_symbol, normalized_timeframe, count=count)
        if raw_payload.get("status") != "OK":
            return self._error_payload(
                normalized_symbol,
                normalized_timeframe,
                count,
                raw_payload.get("status", "HISTORY_UNAVAILABLE"),
                raw_payload.get("message", f"History unavailable for {normalized_symbol} {normalized_timeframe}."),
            )

        candles = self.normalize_candles(raw_payload.get("candles", []))
        validation = self.validate_candles(candles, normalized_timeframe)
        return {
            "symbol": normalized_symbol,
            "timeframe": normalized_timeframe,
            "requested_count": count,
            "returned_count": len(candles),
            "candles": candles,
            "validation": validation,
            "source": raw_payload.get("source", "MT5_DEMO"),
            "broker_source": raw_payload.get("broker_source", raw_payload.get("source", "MT5_DEMO")),
            "account_login": raw_payload.get("account_login", ""),
            "server": raw_payload.get("server", ""),
            "account_type": raw_payload.get("account_type", "DEMO"),
            "status": "OK" if candles else "HISTORY_UNAVAILABLE",
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }

    def normalize_candles(self, raw_candles: list[dict[str, Any]]) -> list[dict[str, Any]]:
        candles: list[dict[str, Any]] = []
        for candle in raw_candles:
            try:
                candles.append(
                    {
                        "time": str(candle["time"]),
                        "open": float(candle["open"]),
                        "high": float(candle["high"]),
                        "low": float(candle["low"]),
                        "close": float(candle["close"]),
                        "tick_volume": int(candle.get("tick_volume", 0) or 0),
                        "source": "MT5_DEMO",
                    }
                )
            except (KeyError, TypeError, ValueError):
                continue
        return candles

    def validate_candles(self, candles: list[dict[str, Any]], timeframe: str = "H1") -> dict[str, Any]:
        warnings: list[str] = []
        if not candles:
            return {
                "valid": False,
                "gaps_detected": False,
                "stale": True,
                "warnings": ["No candles returned from MT5 demo history."],
            }

        valid = True
        previous_time: datetime | None = None
        gaps_detected = False
        expected_seconds = self.timeframe_seconds.get(timeframe, 60 * 60)
        for index, candle in enumerate(candles):
            try:
                open_price = float(candle["open"])
                high = float(candle["high"])
                low = float(candle["low"])
                close = float(candle["close"])
                timestamp = self._parse_time(str(candle["time"]))
            except (KeyError, TypeError, ValueError):
                valid = False
                warnings.append(f"Candle {index} has malformed fields.")
                continue

            if min(open_price, high, low, close) <= 0:
                valid = False
                warnings.append(f"Candle {index} contains non-positive price data.")
            if high < max(open_price, close) or low > min(open_price, close) or high < low:
                valid = False
                warnings.append(f"Candle {index} violates OHLC bounds.")
            if previous_time is not None:
                delta = abs((timestamp - previous_time).total_seconds())
                if delta > expected_seconds * 1.5:
                    gaps_detected = True
            previous_time = timestamp

        stale = self._is_stale(candles[-1]["time"], timeframe)
        if gaps_detected:
            warnings.append("One or more historical candle gaps were detected.")
        if stale:
            warnings.append("Latest historical candle is stale for the requested timeframe.")
        return {
            "valid": valid,
            "gaps_detected": gaps_detected,
            "stale": stale,
            "warnings": warnings,
        }

    def summarize_backfill(self, symbol: str, timeframe: str) -> dict[str, Any]:
        history = self.fetch_history(symbol, timeframe, count=500)
        candles = history.get("candles", [])
        first_time = candles[0]["time"] if candles else None
        last_time = candles[-1]["time"] if candles else None
        return {
            "symbol": history.get("symbol"),
            "timeframe": history.get("timeframe"),
            "requested_count": history.get("requested_count"),
            "returned_count": history.get("returned_count"),
            "first_candle_time": first_time,
            "last_candle_time": last_time,
            "validation": history.get("validation"),
            "status": history.get("status"),
            "source": history.get("source", "MT5_DEMO"),
            "broker_source": history.get("broker_source", history.get("source", "MT5_DEMO")),
            "account_login": history.get("account_login", ""),
            "server": history.get("server", ""),
            "account_type": history.get("account_type", "DEMO"),
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }

    def _error_payload(self, symbol: str, timeframe: str, count: int, status: str, message: str) -> dict[str, Any]:
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "requested_count": count,
            "returned_count": 0,
            "candles": [],
            "validation": {
                "valid": False,
                "gaps_detected": False,
                "stale": True,
                "warnings": [message],
            },
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

    def _is_stale(self, timestamp: str, timeframe: str) -> bool:
        try:
            parsed = self._parse_time(timestamp)
        except ValueError:
            return True
        expected_seconds = self.timeframe_seconds.get(timeframe, 60 * 60)
        return (datetime.now(timezone.utc) - parsed).total_seconds() > expected_seconds * 3

    def _parse_time(self, timestamp: str) -> datetime:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone(timezone.utc)

    def _normalize_symbol(self, symbol: str) -> str:
        return str(symbol or "").strip().upper()

    def _normalize_timeframe(self, timeframe: str) -> str:
        return str(timeframe or "").strip().upper()

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()
