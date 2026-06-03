from backend.nifty50.nifty_candle_store import NIFTYCandleStore
from backend.nifty50.nifty_market_data_models import NIFTYMarketDataHealth
from backend.nifty50.nifty_timeframe_service import NIFTYTimeframeService
from backend.nifty50.nse_market_session import NSEMarketSession


class NIFTYSnapshotBuilder:
    def __init__(
        self,
        candle_store: NIFTYCandleStore | None = None,
        timeframe_service: NIFTYTimeframeService | None = None,
        session_service: NSEMarketSession | None = None,
    ) -> None:
        self.candle_store = candle_store or NIFTYCandleStore()
        self.timeframe_service = timeframe_service or NIFTYTimeframeService(self.candle_store)
        self.session_service = session_service or NSEMarketSession()

    def build_snapshot(self) -> dict:
        latest_tick = self.candle_store.get_latest_tick()
        latest_candle = self.candle_store.get_latest()
        latest_price = latest_tick.price if latest_tick else latest_candle.close if latest_candle else None
        latest_time = latest_tick.timestamp if latest_tick else latest_candle.timestamp if latest_candle else None
        health = self.get_health()
        return {
            "symbol": "NIFTY50",
            "session": self.session_service.get_session_context(),
            "latest_price": latest_price,
            "latest_time": latest_time.isoformat() if latest_time else None,
            "available_timeframes": [
                timeframe
                for timeframe in self.timeframe_service.get_supported_timeframes()
                if self.candle_store.get_by_timeframe(timeframe, limit=1)
            ],
            "data_health": health.model_dump(mode="json"),
            "placeholder": latest_price is None,
            "data_source": "MANUAL_INGESTION" if latest_price is not None else "PLACEHOLDER",
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def get_latest_snapshot(self) -> dict:
        return self.build_snapshot()

    def get_health(self) -> NIFTYMarketDataHealth:
        candles = self.candle_store.get_recent(limit=100000)
        ticks = self.candle_store.get_ticks(limit=100000)
        return NIFTYMarketDataHealth(
            candles_available=len(candles),
            ticks_available=len(ticks),
            valid_candles=len(candles),
            invalid_candles=self.candle_store.invalid_candles,
            supported_timeframes=self.timeframe_service.get_supported_timeframes(),
            data_source="MANUAL_INGESTION" if candles or ticks else "PLACEHOLDER",
            placeholder=not bool(candles or ticks),
        )
