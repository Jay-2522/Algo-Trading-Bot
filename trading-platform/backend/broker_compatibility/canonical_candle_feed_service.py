from typing import Any

from backend.broker_compatibility.broker_registry import BrokerRegistry
from backend.broker_compatibility.canonical_candle_models import MultiTimeframeFeedReport
from backend.broker_compatibility.multi_timeframe_feed_engine import MultiTimeframeFeedEngine


class CanonicalCandleFeedService:
    """Service facade for read-only canonical OHLC feeds."""

    def __init__(
        self,
        registry: BrokerRegistry | None = None,
        feed_engine: MultiTimeframeFeedEngine | None = None,
    ) -> None:
        self.registry = registry or BrokerRegistry()
        self.feed_engine = feed_engine or MultiTimeframeFeedEngine(self.registry)

    def get_status(self) -> dict[str, Any]:
        return {
            "status": "operational",
            "mode": "READ_ONLY_CANONICAL_CANDLE_FEED",
            "supported_timeframes": list(MultiTimeframeFeedEngine.SUPPORTED_TIMEFRAMES),
            "supported_brokers": [broker.broker_id for broker in self.registry.list_brokers()],
            "simulation_only": True,
            "live_execution_enabled": False,
        }

    def get_symbol_feed(self, broker_id: str, symbol: str) -> MultiTimeframeFeedReport:
        return self.feed_engine.build_symbol_feed(broker_id, symbol)

    def get_timeframe_feed(self, broker_id: str, symbol: str, timeframe: str) -> MultiTimeframeFeedReport:
        return self.feed_engine.build_timeframe_feed(broker_id, symbol, timeframe)

    def get_all_feeds(self) -> list[MultiTimeframeFeedReport]:
        return self.feed_engine.build_all_feeds()
