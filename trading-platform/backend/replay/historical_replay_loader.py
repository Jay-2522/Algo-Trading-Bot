from datetime import datetime, timedelta, timezone
import math
from typing import Any


class HistoricalReplayLoader:
    """Load deterministic historical candles with a no-external-data fallback."""

    TIMEFRAME_MINUTES = {"M5": 5, "M15": 15, "H1": 60, "H4": 240}

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
        price = 2000.0 + (sum(ord(char) for char in symbol.upper()) % 100) / 10.0
        for index in range(bounded_limit):
            timestamp = start + timedelta(minutes=minutes * index)
            if end_time and timestamp > end_time:
                break
            trend = index * 0.03
            wave = math.sin(index / 5.0) * 1.4
            open_price = price + trend + wave
            close_price = open_price + math.sin(index / 3.0) * 0.6
            high = max(open_price, close_price) + 0.7 + (index % 4) * 0.08
            low = min(open_price, close_price) - 0.7 - (index % 3) * 0.07
            candles.append(
                {
                    "timestamp": timestamp,
                    "open": round(open_price, 5),
                    "high": round(high, 5),
                    "low": round(low, 5),
                    "close": round(close_price, 5),
                    "volume": 1000 + (index % 50) * 10,
                }
            )
        return candles
