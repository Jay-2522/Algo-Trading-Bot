from backend.market_data.timeframe import SUPPORTED_TIMEFRAMES, get_mt5_timeframe


def validate_symbol_name(symbol: str) -> str:
    """Validate and normalize a market symbol."""

    normalized = symbol.strip().upper() if symbol else ""
    if not normalized:
        raise ValueError("Symbol cannot be empty.")
    return normalized


def validate_candle_count(count: int) -> int:
    """Validate candle request size."""

    if count < 1 or count > 5000:
        raise ValueError("Candle count must be between 1 and 5000.")
    return count


def validate_timeframe(timeframe: str) -> str:
    """Validate and normalize an internal timeframe string."""

    normalized = timeframe.strip().upper() if timeframe else ""
    get_mt5_timeframe(normalized)
    return normalized


def supported_timeframes() -> list[str]:
    return list(SUPPORTED_TIMEFRAMES)

