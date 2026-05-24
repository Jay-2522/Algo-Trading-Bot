def validate_side(side: str) -> str:
    """Validate and normalize an order side."""

    normalized = side.strip().upper() if side else ""
    if normalized not in {"BUY", "SELL"}:
        raise ValueError("Side must be BUY or SELL.")
    return normalized


def validate_order_type(order_type: str) -> str:
    """Validate and normalize an execution order type."""

    normalized = order_type.strip().upper() if order_type else ""
    if normalized not in {"MARKET", "LIMIT", "STOP"}:
        raise ValueError("Order type must be MARKET, LIMIT, or STOP.")
    return normalized


def validate_lot_size(lot_size: float) -> float:
    """Validate simulation size safety bounds."""

    if lot_size <= 0:
        raise ValueError("Lot size must be greater than zero.")
    if lot_size > 100:
        raise ValueError("Lot size cannot exceed 100 in the execution foundation.")
    return lot_size


def validate_price(price: float | None, field_name: str) -> float | None:
    """Validate an optional price when supplied."""

    if price is not None and price <= 0:
        raise ValueError(f"{field_name} must be greater than zero when provided.")
    return price

