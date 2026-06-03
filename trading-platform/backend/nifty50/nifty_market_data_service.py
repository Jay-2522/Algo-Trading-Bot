from backend.nifty50.indian_broker_registry import IndianBrokerRegistry
from backend.nifty50.nifty_candle_store import NIFTYCandleStore
from backend.nifty50.nifty_market_data_adapter import NIFTYMarketDataAdapter
from backend.nifty50.nifty_market_data_models import NIFTYCandle, NIFTYMarketDataHealth, NIFTYTick
from backend.nifty50.nifty_models import NIFTY50Instrument, NIFTY50MarketDataSnapshot
from backend.nifty50.nifty_snapshot_builder import NIFTYSnapshotBuilder
from backend.nifty50.nifty_timeframe_service import NIFTYTimeframeService
from backend.nifty50.nse_market_session import NSEMarketSession


class NIFTYMarketDataService:
    def __init__(
        self,
        session_service: NSEMarketSession | None = None,
        broker_registry: IndianBrokerRegistry | None = None,
        candle_store: NIFTYCandleStore | None = None,
    ) -> None:
        self.session_service = session_service or NSEMarketSession()
        self.broker_registry = broker_registry or IndianBrokerRegistry()
        self.candle_store = candle_store or NIFTYCandleStore()
        self.timeframe_service = NIFTYTimeframeService(self.candle_store)
        self.snapshot_builder = NIFTYSnapshotBuilder(
            candle_store=self.candle_store,
            timeframe_service=self.timeframe_service,
            session_service=self.session_service,
        )
        self.adapter = NIFTYMarketDataAdapter(
            candle_store=self.candle_store,
            snapshot_builder=self.snapshot_builder,
        )

    def get_status(self) -> dict:
        return {
            "status": "MARKET_DATA_READY",
            "instrument": "NIFTY50",
            "market_data_ready": True,
            "data_source": "MANUAL_INGESTION",
            "placeholder": self.get_health().placeholder,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def get_instrument(self) -> NIFTY50Instrument:
        return NIFTY50Instrument()

    def get_snapshot(self) -> NIFTY50MarketDataSnapshot:
        session = self.session_service.get_session_context()
        latest = self.candle_store.get_latest()
        tick = self.candle_store.get_latest_tick()
        latest_price = tick.price if tick else latest.close if latest else None
        return NIFTY50MarketDataSnapshot(
            last_price=latest_price,
            open=latest.open if latest else None,
            high=latest.high if latest else None,
            low=latest.low if latest else None,
            previous_close=None,
            volume=latest.volume if latest else None,
            market_open=bool(session["market_open"]),
            session_name=str(session["session_name"]),
            data_source="MANUAL_INGESTION" if latest_price is not None else "PLACEHOLDER",
            placeholder=latest_price is None,
        )

    def ingest_candle(self, candle: NIFTYCandle) -> dict:
        return self.adapter.ingest_candle(candle)

    def ingest_tick(self, tick: NIFTYTick) -> dict:
        return self.adapter.ingest_tick(tick)

    def get_health(self) -> NIFTYMarketDataHealth:
        return self.adapter.get_health()

    def get_latest(self) -> dict:
        return self.snapshot_builder.get_latest_snapshot()

    def get_supported_timeframes(self) -> list[str]:
        return self.timeframe_service.get_supported_timeframes()

    def get_session_context(self) -> dict:
        return self.session_service.get_session_context()

    def get_broker_candidates(self) -> list[dict]:
        return [broker.model_dump(mode="json") for broker in self.broker_registry.list_brokers()]
