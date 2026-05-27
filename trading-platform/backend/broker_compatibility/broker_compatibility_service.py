from typing import Any

from backend.broker_compatibility.broker_capability_checker import BrokerCapabilityChecker
from backend.broker_compatibility.broker_demo_readiness import BrokerDemoReadinessChecker
from backend.broker_compatibility.broker_demo_verification_service import BrokerDemoVerificationService
from backend.broker_compatibility.broker_feed_quality_models import (
    BrokerFeedQualityReport,
    BrokerSymbolFeedQuality,
)
from backend.broker_compatibility.broker_feed_quality_service import BrokerFeedQualityService
from backend.broker_compatibility.broker_models import (
    BrokerCompatibilityResult,
    BrokerDemoReadinessReport,
    SupportedBroker,
)
from backend.broker_compatibility.broker_observation_models import (
    BrokerObservationReport,
    BrokerObservationStatus,
    BrokerSymbolSnapshot,
)
from backend.broker_compatibility.broker_observation_service import BrokerObservationService
from backend.broker_compatibility.broker_registry import BrokerRegistry
from backend.broker_compatibility.canonical_feed_models import CanonicalFeedReport, CanonicalMarketTick
from backend.broker_compatibility.canonical_feed_service import CanonicalFeedService
from backend.broker_compatibility.canonical_candle_feed_service import CanonicalCandleFeedService
from backend.broker_compatibility.canonical_candle_models import MultiTimeframeFeedReport
from backend.broker_compatibility.mt5_demo_models import (
    BrokerDemoVerificationReport,
    BrokerSymbolVerification,
    MT5TerminalReadiness,
)


class BrokerCompatibilityService:
    """API facade for simulation-only broker compatibility metadata."""

    def __init__(
        self,
        registry: BrokerRegistry | None = None,
        capability_checker: BrokerCapabilityChecker | None = None,
        demo_readiness: BrokerDemoReadinessChecker | None = None,
        demo_verification: BrokerDemoVerificationService | None = None,
        observation_service: BrokerObservationService | None = None,
        feed_quality_service: BrokerFeedQualityService | None = None,
        canonical_feed_service: CanonicalFeedService | None = None,
        candle_feed_service: CanonicalCandleFeedService | None = None,
    ) -> None:
        self.registry = registry or BrokerRegistry()
        self.capability_checker = capability_checker or BrokerCapabilityChecker(self.registry)
        self.demo_readiness = demo_readiness or BrokerDemoReadinessChecker(self.registry, self.capability_checker)
        self.demo_verification = demo_verification or BrokerDemoVerificationService(self.registry)
        self.observation_service = observation_service or BrokerObservationService(self.registry)
        self.feed_quality_service = feed_quality_service or BrokerFeedQualityService(self.registry, self.observation_service)
        self.canonical_feed_service = canonical_feed_service or CanonicalFeedService(self.registry)
        self.candle_feed_service = candle_feed_service or CanonicalCandleFeedService(self.registry)

    def get_status(self) -> dict[str, Any]:
        return {
            "status": "operational",
            "mode": "BROKER_COMPATIBILITY_METADATA_ONLY",
            "supported_brokers": [broker.broker_id for broker in self.registry.list_brokers()],
            "simulation_only": True,
            "live_execution_enabled": False,
        }

    def list_brokers(self) -> list[SupportedBroker]:
        return self.registry.list_brokers()

    def get_broker(self, broker_id: str) -> SupportedBroker | None:
        return self.registry.get_broker(broker_id)

    def check_broker_symbol(self, broker_id: str, symbol: str) -> BrokerCompatibilityResult:
        return self.capability_checker.check_symbol_support(broker_id, symbol)

    def check_broker_all_symbols(self, broker_id: str) -> list[BrokerCompatibilityResult]:
        return self.capability_checker.check_all_client_symbols(broker_id)

    def check_demo_readiness(self, broker_id: str) -> BrokerDemoReadinessReport:
        return self.demo_readiness.check_demo_readiness(broker_id)

    def get_mt5_demo_readiness(self) -> MT5TerminalReadiness:
        return self.demo_verification.get_mt5_readiness()

    def verify_broker_symbols(self, broker_id: str) -> BrokerDemoVerificationReport:
        return self.demo_verification.verify_broker_symbols(broker_id)

    def verify_all_broker_symbols(self) -> list[BrokerDemoVerificationReport]:
        return self.demo_verification.verify_all_brokers()

    def verify_broker_symbol(self, broker_id: str, symbol: str) -> BrokerSymbolVerification:
        return self.demo_verification.verify_symbol_for_broker(broker_id, symbol)

    def get_observation_status(self) -> BrokerObservationStatus:
        return self.observation_service.get_status()

    def observe_broker(self, broker_id: str) -> BrokerObservationReport:
        return self.observation_service.observe_broker(broker_id)

    def observe_all_brokers(self) -> list[BrokerObservationReport]:
        return self.observation_service.observe_all_brokers()

    def snapshot_broker_symbol(self, broker_id: str, symbol: str) -> BrokerSymbolSnapshot:
        return self.observation_service.snapshot_symbol(broker_id, symbol)

    def get_feed_quality_status(self) -> dict[str, Any]:
        return self.feed_quality_service.get_status()

    def check_broker_feed_quality(self, broker_id: str) -> BrokerFeedQualityReport:
        return self.feed_quality_service.check_broker_feed(broker_id)

    def check_all_broker_feed_quality(self) -> list[BrokerFeedQualityReport]:
        return self.feed_quality_service.check_all_broker_feeds()

    def check_broker_symbol_feed_quality(self, broker_id: str, symbol: str) -> BrokerSymbolFeedQuality:
        return self.feed_quality_service.check_symbol_feed(broker_id, symbol)

    def get_canonical_feed_status(self) -> dict[str, Any]:
        return self.canonical_feed_service.get_status()

    def get_canonical_broker_feed(self, broker_id: str) -> CanonicalFeedReport:
        return self.canonical_feed_service.get_broker_feed(broker_id)

    def get_all_canonical_feeds(self) -> list[CanonicalFeedReport]:
        return self.canonical_feed_service.get_all_broker_feeds()

    def get_canonical_symbol_feed(self, broker_id: str, symbol: str) -> CanonicalMarketTick:
        return self.canonical_feed_service.get_symbol_feed(broker_id, symbol)

    def get_candle_feed_status(self) -> dict[str, Any]:
        return self.candle_feed_service.get_status()

    def get_broker_symbol_feed(self, broker_id: str, symbol: str) -> MultiTimeframeFeedReport:
        return self.candle_feed_service.get_symbol_feed(broker_id, symbol)

    def get_broker_timeframe_feed(self, broker_id: str, symbol: str, timeframe: str) -> MultiTimeframeFeedReport:
        return self.candle_feed_service.get_timeframe_feed(broker_id, symbol, timeframe)

    def get_all_broker_feeds(self) -> list[MultiTimeframeFeedReport]:
        return self.candle_feed_service.get_all_feeds()
