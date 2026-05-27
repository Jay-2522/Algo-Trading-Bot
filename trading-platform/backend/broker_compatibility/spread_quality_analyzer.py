class SpreadQualityAnalyzer:
    """Classify spread quality in symbol-specific point units."""

    def classify_spread(self, symbol: str, spread: float | int | None) -> str:
        if spread is None:
            return "INVALID"
        try:
            value = float(spread)
        except Exception:
            return "INVALID"
        if value < 0:
            return "INVALID"

        canonical = str(symbol or "").strip().upper()
        if canonical == "EURUSD":
            if value <= 2:
                return "EXCELLENT"
            if value <= 5:
                return "GOOD"
            if value <= 10:
                return "ACCEPTABLE"
            return "WIDE"
        if canonical == "XAUUSD":
            if value <= 20:
                return "GOOD"
            if value <= 50:
                return "ACCEPTABLE"
            return "WIDE"
        if canonical == "NIFTY50":
            if value <= 5:
                return "GOOD"
            if value <= 15:
                return "ACCEPTABLE"
            return "WIDE"
        if value <= 5:
            return "GOOD"
        if value <= 15:
            return "ACCEPTABLE"
        return "WIDE"
