from backend.replay.client_symbol_models import ClientInstrument, ClientSymbolResolution
from backend.replay.symbol_normalizer import SymbolNormalizer


class ClientSymbolRegistry:
    """Official replay symbol registry for client instruments."""

    def __init__(self, normalizer: SymbolNormalizer | None = None) -> None:
        self.normalizer = normalizer or SymbolNormalizer()
        self._symbols = {
            "EURUSD": ClientInstrument(
                canonical_symbol="EURUSD",
                display_name="EUR/USD",
                market_type="FOREX",
                base_asset="EUR",
                quote_asset="USD",
                broker_aliases=["EUR/USD", "EUR-USD", "eurusd"],
            ),
            "XAUUSD": ClientInstrument(
                canonical_symbol="XAUUSD",
                display_name="XAU/USD Gold",
                market_type="COMMODITY_CFD",
                base_asset="XAU",
                quote_asset="USD",
                broker_aliases=["XAU/USD", "XAU-USD", "GOLD", "gold"],
            ),
            "NIFTY50": ClientInstrument(
                canonical_symbol="NIFTY50",
                display_name="NIFTY 50",
                market_type="INDIAN_INDEX",
                base_asset="NIFTY50",
                quote_asset="INR",
                broker_aliases=["NIFTY 50", "NIFTY50", "NIFTY", "nifty"],
            ),
        }

    def list_supported_symbols(self) -> list[ClientInstrument]:
        return list(self._symbols.values())

    def get_symbol(self, symbol: str) -> ClientInstrument | None:
        return self._symbols.get(self.normalizer.normalize(symbol))

    def is_supported(self, symbol: str) -> bool:
        resolved = self.resolve_symbol(symbol)
        return resolved.supported

    def resolve_symbol(self, symbol: str) -> ClientSymbolResolution:
        canonical = self.normalizer.normalize(symbol)
        instrument = self._symbols.get(canonical)
        if instrument is None:
            return ClientSymbolResolution(
                input_symbol=str(symbol),
                canonical_symbol=canonical or None,
                supported=False,
                market_type=None,
                message=f"{symbol} is not supported for client replay.",
            )
        return ClientSymbolResolution(
            input_symbol=str(symbol),
            canonical_symbol=instrument.canonical_symbol,
            supported=True,
            market_type=instrument.market_type,
            message=f"{symbol} resolved to {instrument.canonical_symbol}.",
        )
