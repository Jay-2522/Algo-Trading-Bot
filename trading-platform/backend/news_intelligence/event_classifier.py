class EventClassifier:
    """Classify macro event titles without external news feeds."""

    SUPPORTED_CATEGORIES = [
        "CPI",
        "NFP",
        "FOMC",
        "PPI",
        "GDP",
        "RETAIL_SALES",
        "PMI",
        "CENTRAL_BANK",
        "EMPLOYMENT",
        "INFLATION",
        "OTHER",
    ]
    SUPPORTED_CURRENCIES = ["USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF"]

    def classify(self, title: str) -> tuple[str, str]:
        normalized = title.upper()
        if "FOMC" in normalized or "FEDERAL RESERVE" in normalized or "RATE DECISION" in normalized:
            return "FOMC", "HIGH"
        if "NONFARM" in normalized or "NON-FARM" in normalized or "NFP" in normalized:
            return "NFP", "HIGH"
        if "CPI" in normalized or "CONSUMER PRICE" in normalized:
            return "CPI", "HIGH"
        if "PPI" in normalized or "PRODUCER PRICE" in normalized:
            return "PPI", "HIGH"
        if "GDP" in normalized:
            return "GDP", "HIGH"
        if "RETAIL SALES" in normalized:
            return "RETAIL_SALES", "MEDIUM"
        if "PMI" in normalized:
            return "PMI", "MEDIUM"
        if "CENTRAL BANK" in normalized or "ECB" in normalized or "BOE" in normalized or "BOJ" in normalized:
            return "CENTRAL_BANK", "HIGH"
        if "JOBLESS" in normalized or "UNEMPLOYMENT" in normalized or "EMPLOYMENT" in normalized:
            return "EMPLOYMENT", "MEDIUM"
        if "INFLATION" in normalized:
            return "INFLATION", "HIGH"
        return "OTHER", "LOW"
