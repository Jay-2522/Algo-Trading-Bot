from backend.broker_compatibility.broker_feed_normalizer import BrokerFeedNormalizer
from backend.broker_compatibility.broker_observation_service import BrokerObservationService
from backend.broker_compatibility.canonical_feed_models import CanonicalFeedReport, CanonicalMarketTick
from backend.broker_compatibility.canonical_feed_quality_resolver import CanonicalFeedQualityResolver
from backend.replay.client_symbol_registry import ClientSymbolRegistry


class CanonicalMarketFeedBuilder:
    """Build AI-ready canonical feed reports from broker observation snapshots."""

    def __init__(
        self,
        observation_service: BrokerObservationService | None = None,
        normalizer: BrokerFeedNormalizer | None = None,
        quality_resolver: CanonicalFeedQualityResolver | None = None,
        symbol_registry: ClientSymbolRegistry | None = None,
    ) -> None:
        self.observation_service = observation_service or BrokerObservationService()
        self.normalizer = normalizer or BrokerFeedNormalizer()
        self.quality_resolver = quality_resolver or CanonicalFeedQualityResolver()
        self.symbol_registry = symbol_registry or ClientSymbolRegistry()

    def build_feed_for_broker(self, broker_id: str) -> CanonicalFeedReport:
        observation = self.observation_service.observe_broker(broker_id)
        ticks = [self._normalize(snapshot) for snapshot in observation.snapshots]
        return self._report(str(broker_id or "").strip().upper(), ticks)

    def build_feed_for_all_brokers(self) -> list[CanonicalFeedReport]:
        return [self.build_feed_for_broker(report.broker_id) for report in self.observation_service.observe_all_brokers()]

    def build_symbol_feed(self, broker_id: str, symbol: str) -> CanonicalMarketTick:
        snapshot = self.observation_service.snapshot_symbol(broker_id, symbol)
        return self._normalize(snapshot)

    def _normalize(self, snapshot) -> CanonicalMarketTick:
        instrument = self.symbol_registry.get_symbol(snapshot.canonical_symbol)
        market_type = instrument.market_type if instrument else None
        tick = self.normalizer.normalize_snapshot(snapshot, market_type=market_type)
        return self.quality_resolver.resolve_tick_quality(tick)

    def _report(self, broker_id: str, ticks: list[CanonicalMarketTick]) -> CanonicalFeedReport:
        usable = [tick.canonical_symbol for tick in ticks if tick.usable and tick.quality in {"GOOD", "WARNING"}]
        unusable = [tick.canonical_symbol for tick in ticks if tick.canonical_symbol not in usable]
        if not ticks or len(unusable) == len(ticks):
            overall = "UNAVAILABLE"
        elif any(tick.quality == "INVALID" for tick in ticks):
            overall = "INVALID"
        elif any(tick.quality in {"WARNING", "UNAVAILABLE"} for tick in ticks):
            overall = "WARNING"
        else:
            overall = "GOOD"
        ai_ready = "EURUSD" in usable and "XAUUSD" in usable
        return CanonicalFeedReport(
            broker_id=broker_id,
            ticks=ticks,
            usable_symbols=usable,
            unusable_symbols=unusable,
            overall_quality=overall,
            ai_ready=ai_ready,
            safety_status="READ_ONLY_CANONICAL_FEED_NORMALIZATION_LIVE_EXECUTION_DISABLED",
            simulation_only=True,
            live_execution_enabled=False,
        )
