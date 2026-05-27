from backend.broker_compatibility.broker_demo_observer import BrokerDemoObserver
from backend.broker_compatibility.broker_observation_models import (
    BrokerObservationReport,
    BrokerObservationStatus,
    BrokerSymbolSnapshot,
)
from backend.broker_compatibility.broker_registry import BrokerRegistry
from backend.broker_compatibility.broker_symbol_snapshotter import BrokerSymbolSnapshotter
from backend.replay.client_symbol_registry import ClientSymbolRegistry


class BrokerObservationService:
    """API-facing read-only broker demo observation service."""

    def __init__(
        self,
        registry: BrokerRegistry | None = None,
        symbol_registry: ClientSymbolRegistry | None = None,
        snapshotter: BrokerSymbolSnapshotter | None = None,
        observer: BrokerDemoObserver | None = None,
    ) -> None:
        self.registry = registry or BrokerRegistry()
        self.symbol_registry = symbol_registry or ClientSymbolRegistry()
        self.snapshotter = snapshotter or BrokerSymbolSnapshotter()
        self.observer = observer or BrokerDemoObserver(self.registry, self.snapshotter)

    def get_status(self) -> BrokerObservationStatus:
        return BrokerObservationStatus(
            status="OPERATIONAL",
            read_only_mode=True,
            supported_brokers=[broker.broker_id for broker in self.registry.list_brokers()],
            supported_symbols=[symbol.canonical_symbol for symbol in self.symbol_registry.list_supported_symbols()],
            simulation_only=True,
            live_execution_enabled=False,
            message="Broker demo observation is available in read-only/simulation-safe mode.",
        )

    def observe_broker(self, broker_id: str) -> BrokerObservationReport:
        return self.observer.observe_broker(broker_id)

    def observe_all_brokers(self) -> list[BrokerObservationReport]:
        return self.observer.observe_all_brokers()

    def snapshot_symbol(self, broker_id: str, symbol: str) -> BrokerSymbolSnapshot:
        return self.snapshotter.snapshot_symbol(broker_id, symbol)
