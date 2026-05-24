from backend.market_data.validators import validate_symbol_name, validate_timeframe


def validate_strategy_symbol(symbol: str) -> str:
    """Validate a strategy analysis symbol."""

    return validate_symbol_name(symbol)


def validate_strategy_timeframe(timeframe: str) -> str:
    """Validate a strategy analysis timeframe."""

    return validate_timeframe(timeframe)

