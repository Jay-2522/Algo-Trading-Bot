from datetime import datetime, timezone
from typing import Any

from backend.mt5_demo.mt5_market_data_service import MT5MarketDataService


class MarketSnapshotService:
    """Central read-only MT5 demo market snapshot pipeline."""

    symbols = ["EURUSD", "XAUUSD"]
    candle_timeframes = ["M5", "H1"]

    def __init__(self, market_data_service: MT5MarketDataService | None = None) -> None:
        self.market_data_service = market_data_service or MT5MarketDataService()

    def get_overview(self) -> dict[str, Any]:
        symbols = {symbol: self._symbol_snapshot(symbol) for symbol in self.symbols}
        overall_status = self._overall_status(symbols)
        return {
            "symbols": symbols,
            "eurusd": symbols["EURUSD"],
            "xauusd": symbols["XAUUSD"],
            "last_update": self._timestamp(),
            "status": overall_status,
            "source": "MT5_DEMO",
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
        }

    def _symbol_snapshot(self, symbol: str) -> dict[str, Any]:
        tick = self.market_data_service.get_symbol_tick(symbol)
        spread = self.market_data_service.get_symbol_spread(symbol)
        candle_payloads = {
            timeframe: self.market_data_service.get_symbol_candles(symbol, timeframe, count=1)
            for timeframe in self.candle_timeframes
        }
        candle_timestamps = {
            timeframe: self._latest_candle_time(payload)
            for timeframe, payload in candle_payloads.items()
        }
        freshest_timestamp = self._freshest_timestamp([tick.get("timestamp"), *candle_timestamps.values()])
        freshness = self.calculate_freshness(freshest_timestamp)
        availability_status = self._availability_status(tick, candle_payloads, freshness)
        return {
            "symbol": symbol,
            "bid": tick.get("bid") if tick.get("status") == "OK" else None,
            "ask": tick.get("ask") if tick.get("status") == "OK" else None,
            "spread": spread.get("spread") if spread.get("status") == "OK" else None,
            "tick_status": tick.get("status"),
            "tick_message": tick.get("message"),
            "tick_timestamp": tick.get("timestamp"),
            "latest_candle_timestamps": candle_timestamps,
            "freshest_timestamp": freshest_timestamp,
            "freshness": freshness,
            "availability_status": availability_status,
            "source": "MT5_DEMO",
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
        }

    def calculate_freshness(self, timestamp: str | None) -> str:
        if not timestamp:
            return "OFFLINE"
        try:
            parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            return "OFFLINE"
        age_minutes = (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds() / 60
        if age_minutes < 5:
            return "READY"
        if age_minutes <= 30:
            return "STALE"
        return "OFFLINE"

    def _availability_status(self, tick: dict[str, Any], candles: dict[str, dict[str, Any]], freshness: str) -> str:
        if tick.get("status") == "OK" and freshness == "READY":
            return "TICK_READY"
        if any(payload.get("status") == "OK" and payload.get("count", 0) > 0 for payload in candles.values()):
            return "CANDLES_AVAILABLE"
        if tick.get("status") == "STALE_OR_UNAVAILABLE":
            return "TICK_STALE_OR_UNAVAILABLE"
        return "UNAVAILABLE"

    def _overall_status(self, symbols: dict[str, dict[str, Any]]) -> str:
        if any(item.get("freshness") == "READY" for item in symbols.values()):
            return "READY"
        if any(item.get("freshness") == "STALE" for item in symbols.values()):
            return "STALE"
        return "OFFLINE"

    def _latest_candle_time(self, payload: dict[str, Any]) -> str | None:
        candles = payload.get("candles")
        if not isinstance(candles, list) or not candles:
            return None
        latest = candles[-1]
        return str(latest.get("time")) if isinstance(latest, dict) and latest.get("time") else None

    def _freshest_timestamp(self, timestamps: list[Any]) -> str | None:
        parsed: list[tuple[datetime, str]] = []
        for timestamp in timestamps:
            if not timestamp:
                continue
            try:
                dt = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00")).astimezone(timezone.utc)
                if dt.timestamp() > 0:
                    parsed.append((dt, str(timestamp)))
            except ValueError:
                continue
        if not parsed:
            return None
        return max(parsed, key=lambda item: item[0])[1]

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()
