from backend.broker_compatibility.broker_models import BrokerCompatibilityResult
from backend.broker_compatibility.broker_registry import BrokerRegistry
from backend.broker_compatibility.broker_symbol_mapper import BrokerSymbolMapper


class BrokerCapabilityChecker:
    """Check theoretical broker compatibility without broker API calls."""

    def __init__(
        self,
        registry: BrokerRegistry | None = None,
        mapper: BrokerSymbolMapper | None = None,
    ) -> None:
        self.registry = registry or BrokerRegistry()
        self.mapper = mapper or BrokerSymbolMapper(self.registry)

    def check_symbol_support(self, broker_id: str, canonical_symbol: str) -> BrokerCompatibilityResult:
        broker = self.registry.get_broker(broker_id)
        mapping = self.mapper.map_symbol(broker_id, canonical_symbol)
        if broker is None:
            return BrokerCompatibilityResult(
                broker_id=str(broker_id or "").strip().upper(),
                canonical_symbol=mapping.canonical_symbol,
                broker_symbol=mapping.broker_symbol,
                supported=False,
                demo_ready=False,
                read_only_supported=False,
                live_execution_enabled=False,
                message="Broker is not supported by compatibility metadata.",
            )
        supported = mapping.supported
        return BrokerCompatibilityResult(
            broker_id=broker.broker_id,
            canonical_symbol=mapping.canonical_symbol,
            broker_symbol=mapping.broker_symbol,
            supported=supported,
            demo_ready=supported,
            read_only_supported=supported,
            live_execution_enabled=False,
            message=mapping.notes,
        )

    def check_all_client_symbols(self, broker_id: str) -> list[BrokerCompatibilityResult]:
        return [
            self.check_symbol_support(broker_id, mapping.canonical_symbol)
            for mapping in self.mapper.list_symbol_mappings(broker_id)
        ]
