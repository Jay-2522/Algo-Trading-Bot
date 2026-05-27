from backend.broker_compatibility.broker_observation_models import BrokerObservationReport
from backend.broker_compatibility.broker_observation_report_builder import BrokerObservationReportBuilder
from backend.broker_compatibility.broker_registry import BrokerRegistry
from backend.broker_compatibility.broker_symbol_snapshotter import BrokerSymbolSnapshotter


class BrokerDemoObserver:
    """Coordinate read-only demo observation for supported brokers."""

    def __init__(
        self,
        registry: BrokerRegistry | None = None,
        snapshotter: BrokerSymbolSnapshotter | None = None,
        report_builder: BrokerObservationReportBuilder | None = None,
    ) -> None:
        self.registry = registry or BrokerRegistry()
        self.snapshotter = snapshotter or BrokerSymbolSnapshotter()
        self.report_builder = report_builder or BrokerObservationReportBuilder()

    def observe_broker(self, broker_id: str) -> BrokerObservationReport:
        broker = self.registry.get_broker(broker_id)
        normalized = str(broker_id or "").strip().upper()
        if broker is None:
            return self.report_builder.build_report(normalized, [])
        snapshots = self.snapshotter.snapshot_all_symbols(broker.broker_id)
        return self.report_builder.build_report(broker.broker_id, snapshots)

    def observe_all_brokers(self) -> list[BrokerObservationReport]:
        return [self.observe_broker(broker.broker_id) for broker in self.registry.list_brokers()]
