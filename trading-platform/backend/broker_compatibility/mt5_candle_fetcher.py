from datetime import datetime, timezone
from typing import Any

try:
    import MetaTrader5 as imported_mt5  # type: ignore
except Exception:  # pragma: no cover - depends on local terminal package
    imported_mt5 = None

from backend.replay.historical_replay_loader import HistoricalReplayLoader
from backend.replay.symbol_normalizer import SymbolNormalizer


class MT5CandleFetcher:
    """Read-only MT5 candle fetcher with deterministic simulation fallback."""

    SUPPORTED_TIMEFRAMES = ("M5", "M15", "H1", "H4")

    def __init__(
        self,
        mt5_module: Any | None = None,
        loader: HistoricalReplayLoader | None = None,
        normalizer: SymbolNormalizer | None = None,
        force_fallback: bool = False,
    ) -> None:
        self.mt5 = imported_mt5 if mt5_module is None else mt5_module
        self.loader = loader or HistoricalReplayLoader()
        self.normalizer = normalizer or SymbolNormalizer()
        self.force_fallback = force_fallback

    def fetch_candles(self, symbol: str, timeframe: str, count: int = 100) -> list[dict[str, Any]]:
        tf = str(timeframe or "").strip().upper()
        if tf not in self.SUPPORTED_TIMEFRAMES:
            return self._fallback_candles(symbol, tf or "M15", count)
        if self.force_fallback or self.mt5 is None:
            return self._fallback_candles(symbol, tf, count)

        try:
            tf_constant = self._timeframe_constant(tf)
            if tf_constant is None:
                return self._fallback_candles(symbol, tf, count)
            initialized = bool(self.mt5.initialize())
            if not initialized:
                return self._fallback_candles(symbol, tf, count)
            rates = self.mt5.copy_rates_from_pos(str(symbol).upper(), tf_constant, 0, max(1, min(int(count), 5000)))
            if rates is None or len(rates) == 0:
                return self._fallback_candles(symbol, tf, count)
            candles: list[dict[str, Any]] = []
            for rate in rates:
                item = self._rate_to_dict(rate)
                item["source"] = "MT5_READ_ONLY"
                candles.append(item)
            return candles
        except Exception:
            return self._fallback_candles(symbol, tf, count)
        finally:
            try:
                self.mt5.shutdown()
            except Exception:
                pass

    def _timeframe_constant(self, timeframe: str) -> Any | None:
        names = {
            "M5": "TIMEFRAME_M5",
            "M15": "TIMEFRAME_M15",
            "H1": "TIMEFRAME_H1",
            "H4": "TIMEFRAME_H4",
        }
        return getattr(self.mt5, names[timeframe], None)

    def _rate_to_dict(self, rate: Any) -> dict[str, Any]:
        def read(key: str, default: Any = None) -> Any:
            if isinstance(rate, dict):
                return rate.get(key, default)
            try:
                return rate[key]
            except Exception:
                return getattr(rate, key, default)

        timestamp = read("time")
        if isinstance(timestamp, (int, float)):
            parsed_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        else:
            parsed_time = timestamp
        return {
            "timestamp": parsed_time,
            "open": read("open"),
            "high": read("high"),
            "low": read("low"),
            "close": read("close"),
            "volume": read("tick_volume", read("volume", 0)),
        }

    def _fallback_candles(self, symbol: str, timeframe: str, count: int) -> list[dict[str, Any]]:
        canonical = self.normalizer.normalize(symbol)
        candles = self.loader.load_candles(canonical, timeframe, limit=max(1, min(int(count), 5000)))
        for candle in candles:
            candle["source"] = "SIMULATION_FALLBACK"
        return candles
