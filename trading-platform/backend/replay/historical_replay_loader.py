from datetime import datetime, timedelta, timezone
import math
from typing import Any

from backend.replay.symbol_normalizer import SymbolNormalizer


class HistoricalReplayLoader:
    """Load deterministic historical candles with a no-external-data fallback."""

    TIMEFRAME_MINUTES = {"M5": 5, "M15": 15, "H1": 60, "H4": 240}
    SYMBOL_PROFILES = {
        "EURUSD": {"base": 1.1, "trend": 0.000003, "wave": 0.004, "body": 0.0012, "wick": 0.0015, "digits": 5},
        "XAUUSD": {"base": 2400.0, "trend": 0.03, "wave": 14.0, "body": 6.0, "wick": 7.0, "digits": 2},
        "NIFTY50": {"base": 22000.0, "trend": 0.8, "wave": 120.0, "body": 45.0, "wick": 55.0, "digits": 2},
    }

    def __init__(self, normalizer: SymbolNormalizer | None = None) -> None:
        self.normalizer = normalizer or SymbolNormalizer()

    def load_candles(
        self,
        symbol: str,
        timeframe: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        tf = timeframe.strip().upper()
        if tf not in self.TIMEFRAME_MINUTES:
            raise ValueError(f"Unsupported replay timeframe: {timeframe}")
        bounded_limit = max(1, min(int(limit), 5000))
        minutes = self.TIMEFRAME_MINUTES[tf]
        start = start_time or datetime(2024, 1, 1, tzinfo=timezone.utc)
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        candles: list[dict[str, Any]] = []
        canonical = self.normalizer.normalize(symbol)
        profile = self.SYMBOL_PROFILES.get(
            canonical,
            {"base": 2000.0, "trend": 0.03, "wave": 1.4, "body": 0.6, "wick": 0.7, "digits": 5},
        )
        seed = (sum(ord(char) for char in canonical.upper()) % 25) * float(profile["body"]) * 0.01
        price = float(profile["base"]) + seed
        for index in range(bounded_limit):
            timestamp = start + timedelta(minutes=minutes * index)
            if end_time and timestamp > end_time:
                break
            trend = index * float(profile["trend"])
            wave = math.sin(index / 5.0) * float(profile["wave"])
            open_price = price + trend + wave
            close_price = open_price + math.sin(index / 3.0) * float(profile["body"])
            high = max(open_price, close_price) + float(profile["wick"]) + (index % 4) * float(profile["wick"]) * 0.1
            low = min(open_price, close_price) - float(profile["wick"]) - (index % 3) * float(profile["wick"]) * 0.1
            digits = int(profile["digits"])
            candles.append(
                {
                    "timestamp": timestamp,
                    "open": round(open_price, digits),
                    "high": round(high, digits),
                    "low": round(low, digits),
                    "close": round(close_price, digits),
                    "volume": 1000 + (index % 50) * 10,
                }
            )
        return candles
