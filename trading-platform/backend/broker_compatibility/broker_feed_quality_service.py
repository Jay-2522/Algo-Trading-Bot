from backend.broker_compatibility.broker_feed_quality_models import (
    BrokerFeedQualityReport,
    BrokerSymbolFeedQuality,
)
from backend.broker_compatibility.broker_feed_quality_report_builder import BrokerFeedQualityReportBuilder
from backend.broker_compatibility.broker_observation_service import BrokerObservationService
from backend.broker_compatibility.broker_registry import BrokerRegistry


class BrokerFeedQualityService:
    """Broker feed quality validation facade."""

    def __init__(
        self,
        registry: BrokerRegistry | None = None,
        observation_service: BrokerObservationService | None = None,
        report_builder: BrokerFeedQualityReportBuilder | None = None,
    ) -> None:
        self.registry = registry or BrokerRegistry()
        self.observation_service = observation_service or BrokerObservationService(self.registry)
        self.report_builder = report_builder or BrokerFeedQualityReportBuilder()

    def get_status(self) -> dict:
        return {
            "status": "operational",
            "mode": "READ_ONLY_BROKER_FEED_VALIDATION",
            "supported_brokers": [broker.broker_id for broker in self.registry.list_brokers()],
            "simulation_only": True,
            "live_execution_enabled": False,
        }

    def check_broker_feed(self, broker_id: str) -> BrokerFeedQualityReport:
        observation = self.observation_service.observe_broker(broker_id)
        return self.report_builder.build_report(broker_id, observation.snapshots)

    def check_all_broker_feeds(self) -> list[BrokerFeedQualityReport]:
        return [self.check_broker_feed(broker.broker_id) for broker in self.registry.list_brokers()]

    def check_symbol_feed(self, broker_id: str, symbol: str) -> BrokerSymbolFeedQuality:
        snapshot = self.observation_service.snapshot_symbol(broker_id, symbol)
        return self.report_builder.validator.validate_snapshot(snapshot)
