from backend.replay.symbol_normalizer import SymbolNormalizer


class SymbolRiskRules:
    """Symbol-specific allocation risk limits."""

    RULES = {
        "EURUSD": {"symbol": "EURUSD", "max_total_lot": 3.0, "max_risk": 1.0, "blocked": False},
        "XAUUSD": {"symbol": "XAUUSD", "max_total_lot": 1.0, "max_risk": 0.75, "blocked": False},
        "NIFTY50": {
            "symbol": "NIFTY50",
            "max_total_lot": 0.0,
            "max_risk": 0.0,
            "blocked": True,
            "reason": "NIFTY50 allocation is blocked until Indian broker integration is implemented.",
        },
    }

    def __init__(self, normalizer: SymbolNormalizer | None = None) -> None:
        self.normalizer = normalizer or SymbolNormalizer()

    def get_rules(self, symbol: str) -> dict:
        canonical = self.normalizer.normalize(symbol)
        return self.RULES.get(
            canonical,
            {
                "symbol": canonical,
                "max_total_lot": 0.0,
                "max_risk": 0.0,
                "blocked": True,
                "reason": "Symbol is unsupported for allocation.",
            },
        )
