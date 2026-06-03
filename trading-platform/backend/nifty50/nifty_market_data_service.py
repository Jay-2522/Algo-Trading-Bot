from backend.nifty50.indian_broker_registry import IndianBrokerRegistry
from backend.nifty50.nifty_models import NIFTY50Instrument, NIFTY50MarketDataSnapshot
from backend.nifty50.nse_market_session import NSEMarketSession


class NIFTYMarketDataService:
    def __init__(
        self,
        session_service: NSEMarketSession | None = None,
        broker_registry: IndianBrokerRegistry | None = None,
    ) -> None:
        self.session_service = session_service or NSEMarketSession()
        self.broker_registry = broker_registry or IndianBrokerRegistry()

    def get_status(self) -> dict:
        return {
            "status": "FOUNDATION_READY",
            "instrument": "NIFTY50",
            "market_data_ready": False,
            "data_source": "PLACEHOLDER",
            "placeholder": True,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def get_instrument(self) -> NIFTY50Instrument:
        return NIFTY50Instrument()

    def get_snapshot(self) -> NIFTY50MarketDataSnapshot:
        session = self.session_service.get_session_context()
        return NIFTY50MarketDataSnapshot(
            market_open=bool(session["market_open"]),
            session_name=str(session["session_name"]),
            data_source="PLACEHOLDER",
            placeholder=True,
        )

    def get_session_context(self) -> dict:
        return self.session_service.get_session_context()

    def get_broker_candidates(self) -> list[dict]:
        return [broker.model_dump(mode="json") for broker in self.broker_registry.list_brokers()]
