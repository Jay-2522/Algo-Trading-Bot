from backend.replay.client_symbol_registry import ClientSymbolRegistry


class TradingViewSignalClassifier:
    """Classify normalized client symbols into market types."""

    def __init__(self, symbol_registry: ClientSymbolRegistry | None = None) -> None:
        self.symbol_registry = symbol_registry or ClientSymbolRegistry()

    def classify(self, signal_or_symbol) -> str:
        symbol = getattr(signal_or_symbol, "canonical_symbol", signal_or_symbol)
        instrument = self.symbol_registry.get_symbol(str(symbol))
        return instrument.market_type if instrument else "UNKNOWN"
