from backend.broker_compatibility.broker_registry import BrokerRegistry
from backend.broker_compatibility.canonical_feed_models import CanonicalFeedReport, CanonicalMarketTick
from backend.broker_compatibility.canonical_market_feed_builder import CanonicalMarketFeedBuilder


class CanonicalFeedService:
    """Service facade for read-only canonical market feed normalization."""

    def __init__(
        self,
        registry: BrokerRegistry | None = None,
        builder: CanonicalMarketFeedBuilder | None = None,
    ) -> None:
        self.registry = registry or BrokerRegistry()
        self.builder = builder or CanonicalMarketFeedBuilder()

    def get_status(self) -> dict:
        return {
            "status": "operational",
            "mode": "READ_ONLY_CANONICAL_MARKET_FEED",
            "supported_brokers": [broker.broker_id for broker in self.registry.list_brokers()],
            "simulation_only": True,
            "live_execution_enabled": False,
        }

    def get_broker_feed(self, broker_id: str) -> CanonicalFeedReport:
        return self.builder.build_feed_for_broker(broker_id)

    def get_all_broker_feeds(self) -> list[CanonicalFeedReport]:
        return [self.get_broker_feed(broker.broker_id) for broker in self.registry.list_brokers()]

    def get_symbol_feed(self, broker_id: str, symbol: str) -> CanonicalMarketTick:
        return self.builder.build_symbol_feed(broker_id, symbol)
