SUPPORTED_CATEGORIES = {
    "CPI",
    "NFP",
    "FOMC",
    "FED_SPEECH",
    "GDP",
    "JOBLESS_CLAIMS",
    "PMI",
    "OTHER",
}
SUPPORTED_IMPACT_LEVELS = {"LOW", "MEDIUM", "HIGH"}


def validate_currency(currency: str) -> str:
    normalized = currency.strip().upper() if currency else ""
    if len(normalized) != 3 or not normalized.isalpha():
        raise ValueError("Currency must be a three-letter alphabetic code.")
    return normalized


def validate_event_category(category: str) -> str:
    normalized = category.strip().upper() if category else ""
    if normalized not in SUPPORTED_CATEGORIES:
        raise ValueError(f"Unsupported economic event category: {category}.")
    return normalized


def validate_impact_level(impact: str) -> str:
    normalized = impact.strip().upper() if impact else ""
    if normalized not in SUPPORTED_IMPACT_LEVELS:
        raise ValueError(f"Unsupported impact level: {impact}.")
    return normalized

