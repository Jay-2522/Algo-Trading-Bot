def validate_positive_number(value: float, field_name: str) -> float:
    """Require a strictly positive numeric input."""

    if value <= 0:
        raise ValueError(f"{field_name} must be greater than zero.")
    return value


def validate_risk_percent(risk_percent: float) -> float:
    """Validate calculation-level percentage bounds."""

    if risk_percent <= 0 or risk_percent > 5:
        raise ValueError("Risk percent must be greater than 0 and less than or equal to 5.")
    return risk_percent


def validate_drawdown(drawdown_percent: float) -> float:
    """Validate that reported drawdown is non-negative."""

    if drawdown_percent < 0:
        raise ValueError("Current drawdown percent cannot be negative.")
    return drawdown_percent


def validate_spread(spread: float) -> float:
    """Validate a non-negative spread measurement."""

    if spread < 0:
        raise ValueError("Current spread cannot be negative.")
    return spread


def validate_slippage(slippage: float) -> float:
    """Validate a non-negative slippage estimate."""

    if slippage < 0:
        raise ValueError("Expected slippage cannot be negative.")
    return slippage

