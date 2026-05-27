class SymbolNormalizer:
    """Normalize client-facing instrument aliases into canonical replay symbols."""

    ALIAS_MAP = {
        "EURUSD": "EURUSD",
        "XAUUSD": "XAUUSD",
        "GOLD": "XAUUSD",
        "NIFTY50": "NIFTY50",
        "NIFTY": "NIFTY50",
    }

    def normalize(self, symbol: str) -> str:
        cleaned = str(symbol or "").strip().upper().replace("/", "").replace("-", "").replace(" ", "")
        return self.ALIAS_MAP.get(cleaned, cleaned)
