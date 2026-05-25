import hashlib
import math
import random
from datetime import datetime, timedelta, timezone

from backend.backtesting.backtest_models import BacktestRequest, HistoricalCandle


class HistoricalDataLoader:
    """Generate reproducible OHLCV bars until an external historical feed is added."""

    TIMEFRAME_MINUTES = {"M1": 1, "M5": 5, "M15": 15, "H1": 60, "H4": 240}

    def load_candles(self, request: BacktestRequest) -> list[HistoricalCandle]:
        interval = timedelta(minutes=self.TIMEFRAME_MINUTES[request.timeframe])
        start = self._as_utc(request.start_date)
        end = self._as_utc(request.end_date)
        available_bars = int((end - start) / interval) + 1
        candle_count = min(request.max_candles, max(available_bars, 0))
        if candle_count <= 0:
            return []

        seed_text = f"{request.symbol}:{request.timeframe}:{start.isoformat()}:{end.isoformat()}"
        seed = int(hashlib.sha256(seed_text.encode("ascii")).hexdigest()[:16], 16)
        rng = random.Random(seed)
        base_price = 2300.0 if request.symbol == "XAUUSD" else 100.0
        price = base_price
        candles: list[HistoricalCandle] = []

        for index in range(candle_count):
            regime = 1 if (index // 110) % 2 == 0 else -1
            trend_move = regime * base_price * 0.00010
            cyclical_move = math.sin(index / 13.0) * base_price * 0.00005
            noise = rng.uniform(-1, 1) * base_price * 0.00008
            candle_open = price
            candle_close = max(0.00001, candle_open + trend_move + cyclical_move + noise)
            wick = abs(rng.uniform(0.00004, 0.00018) * base_price)
            candle_high = max(candle_open, candle_close) + wick
            candle_low = max(0.00001, min(candle_open, candle_close) - wick)
            volume = int(100 + abs(trend_move + noise) * 1000 + rng.randint(0, 250))
            candles.append(
                HistoricalCandle(
                    timestamp=start + interval * index,
                    open=round(candle_open, 5),
                    high=round(candle_high, 5),
                    low=round(candle_low, 5),
                    close=round(candle_close, 5),
                    volume=volume,
                )
            )
            price = candle_close
        return candles

    def _as_utc(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
