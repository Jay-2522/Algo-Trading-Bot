from backend.broker_compatibility.broker_models import BrokerSymbolMapping
from backend.broker_compatibility.broker_registry import BrokerRegistry
from backend.replay.client_symbol_registry import ClientSymbolRegistry


class BrokerSymbolMapper:
    """Map canonical client symbols into broker-facing symbol names conservatively."""

    def __init__(
        self,
        broker_registry: BrokerRegistry | None = None,
        symbol_registry: ClientSymbolRegistry | None = None,
    ) -> None:
        self.broker_registry = broker_registry or BrokerRegistry()
        self.symbol_registry = symbol_registry or ClientSymbolRegistry()

    def map_symbol(self, broker_id: str, canonical_symbol: str) -> BrokerSymbolMapping:
        broker_id = str(broker_id or "").strip().upper()
        resolution = self.symbol_registry.resolve_symbol(canonical_symbol)
        canonical = resolution.canonical_symbol or str(canonical_symbol or "").strip().upper()
        instrument = self.symbol_registry.get_symbol(canonical)

        if not self.broker_registry.is_supported_broker(broker_id):
            return BrokerSymbolMapping(
                broker_id=broker_id,
                canonical_symbol=canonical,
                broker_symbol=None,
                supported=False,
                market_type=instrument.market_type if instrument else "UNKNOWN",
                notes="Broker is not registered in compatibility metadata.",
            )
        if instrument is None:
            return BrokerSymbolMapping(
                broker_id=broker_id,
                canonical_symbol=canonical,
                broker_symbol=None,
                supported=False,
                market_type="UNKNOWN",
                notes="Client instrument is not supported by the replay symbol registry.",
            )

        if canonical in {"EURUSD", "XAUUSD"}:
            return BrokerSymbolMapping(
                broker_id=broker_id,
                canonical_symbol=canonical,
                broker_symbol=canonical,
                supported=True,
                market_type=instrument.market_type,
                notes="Requires broker symbol verification in MT5 demo terminal before any read-only integration.",
            )

        return BrokerSymbolMapping(
            broker_id=broker_id,
            canonical_symbol=canonical,
            broker_symbol="NIFTY50",
            supported=False,
            market_type=instrument.market_type,
            notes="NIFTY50 availability is broker-dependent; verify in the demo terminal before marking supported. Treated as unsupported/conditional for now.",
        )

    def list_symbol_mappings(self, broker_id: str) -> list[BrokerSymbolMapping]:
        return [
            self.map_symbol(broker_id, instrument.canonical_symbol)
            for instrument in self.symbol_registry.list_supported_symbols()
        ]
