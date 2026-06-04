from backend.nifty50.nifty_market_data_models import NIFTYCandle, NIFTYTick


class NIFTYCandleStore:
    def __init__(self) -> None:
        self._candles: list[NIFTYCandle] = []
        self._ticks: list[NIFTYTick] = []
        self.invalid_candles = 0

    def add_candle(self, candle: NIFTYCandle) -> NIFTYCandle:
        for index, existing in enumerate(self._candles):
            if (
                existing.symbol.upper() == candle.symbol.upper()
                and existing.timeframe.upper() == candle.timeframe.upper()
                and existing.timestamp == candle.timestamp
            ):
                self._candles[index] = candle
                self._candles.sort(key=lambda item: item.timestamp)
                return candle
        self._candles.append(candle)
        self._candles.sort(key=lambda item: item.timestamp)
        return candle

    def add_tick(self, tick: NIFTYTick) -> NIFTYTick:
        for index, existing in enumerate(self._ticks):
            if existing.symbol.upper() == tick.symbol.upper() and existing.timestamp == tick.timestamp:
                self._ticks[index] = tick
                self._ticks.sort(key=lambda item: item.timestamp)
                return tick
        self._ticks.append(tick)
        self._ticks.sort(key=lambda item: item.timestamp)
        return tick

    def record_invalid_candle(self) -> None:
        self.invalid_candles += 1

    def get_recent(self, limit: int = 100) -> list[NIFTYCandle]:
        return self._candles[-limit:]

    def get_by_timeframe(self, timeframe: str, limit: int = 100) -> list[NIFTYCandle]:
        normalized = timeframe.upper()
        return [candle for candle in self._candles if candle.timeframe.upper() == normalized][-limit:]

    def get_latest(self, timeframe: str | None = None) -> NIFTYCandle | None:
        candles = self.get_by_timeframe(timeframe) if timeframe else self._candles
        return candles[-1] if candles else None

    def get_latest_tick(self) -> NIFTYTick | None:
        return self._ticks[-1] if self._ticks else None

    def get_ticks(self, limit: int = 100) -> list[NIFTYTick]:
        return self._ticks[-limit:]

    def clear(self) -> None:
        self._candles.clear()
        self._ticks.clear()
        self.invalid_candles = 0
