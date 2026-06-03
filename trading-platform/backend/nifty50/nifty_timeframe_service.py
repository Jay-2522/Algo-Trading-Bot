from backend.nifty50.nifty_candle_store import NIFTYCandleStore
from backend.nifty50.nifty_market_data_models import NIFTYCandle


class NIFTYTimeframeService:
    supported_timeframes = ["M1", "M5", "M15", "H1", "H4", "D1"]

    def __init__(self, candle_store: NIFTYCandleStore | None = None) -> None:
        self.candle_store = candle_store or NIFTYCandleStore()

    def get_supported_timeframes(self) -> list[str]:
        return self.supported_timeframes

    def aggregate(self, source_timeframe: str = "M1", target_timeframe: str = "M5", limit: int = 100) -> list[NIFTYCandle]:
        if target_timeframe.upper() not in self.supported_timeframes:
            return []
        # Phase 12 Day 3 keeps aggregation architecture-only. Return existing candles for the requested timeframe.
        existing = self.candle_store.get_by_timeframe(target_timeframe, limit=limit)
        if existing:
            return existing
        return self.candle_store.get_by_timeframe(source_timeframe, limit=limit)

    def get_latest_by_timeframe(self, timeframe: str) -> NIFTYCandle | None:
        return self.candle_store.get_latest(timeframe)
