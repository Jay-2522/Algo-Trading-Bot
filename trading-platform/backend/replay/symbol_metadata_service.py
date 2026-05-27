from backend.replay.client_symbol_models import ClientInstrument
from backend.replay.client_symbol_registry import ClientSymbolRegistry


class SymbolMetadataService:
    """Metadata lookup for official client replay instruments."""

    def __init__(self, registry: ClientSymbolRegistry | None = None) -> None:
        self.registry = registry or ClientSymbolRegistry()

    def get_metadata(self, symbol: str) -> ClientInstrument | None:
        return self.registry.get_symbol(symbol)

    def list_metadata(self) -> list[ClientInstrument]:
        return self.registry.list_supported_symbols()
