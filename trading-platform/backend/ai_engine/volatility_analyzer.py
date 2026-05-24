class VolatilityAnalyzer:
    """Safe foundation volatility assessment without external model dependencies."""

    def evaluate_volatility(self, symbol: str, percentage_range: float | None = None) -> dict:
        normalized_symbol = symbol.strip().upper() if symbol else ""
        if not normalized_symbol:
            raise ValueError("Symbol cannot be empty.")
        measure = percentage_range if percentage_range is not None else 0.8
        level = self.classify_volatility_level(measure)
        quality_score = {"LOW": 75, "NORMAL": 85, "HIGH": 35, "EXTREME": 10}[level]
        return {
            "symbol": normalized_symbol,
            "volatility_level": level,
            "quality_score": quality_score,
            "measurement": measure,
            "method": "foundation_range_estimate",
        }

    def classify_volatility_level(self, percentage_range: float) -> str:
        if percentage_range < 0:
            raise ValueError("Volatility measurement cannot be negative.")
        if percentage_range >= 4.0:
            return "EXTREME"
        if percentage_range >= 2.0:
            return "HIGH"
        if percentage_range >= 0.4:
            return "NORMAL"
        return "LOW"

