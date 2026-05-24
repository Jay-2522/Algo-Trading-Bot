from backend.execution_engine.execution_models import OrderRequest, OrderValidationResult
from backend.execution_engine.validators import (
    validate_lot_size,
    validate_order_type,
    validate_price,
    validate_side,
)


class OrderValidator:
    """Validate execution requests before any simulation or future broker flow."""

    def validate_order(self, order: OrderRequest) -> OrderValidationResult:
        errors: list[str] = []
        warnings: list[str] = []

        if not order.symbol or not order.symbol.strip():
            errors.append("Symbol cannot be empty.")

        for validator, value in (
            (validate_side, order.side),
            (validate_order_type, order.order_type),
            (validate_lot_size, order.lot_size),
        ):
            try:
                validator(value)
            except ValueError as exc:
                errors.append(str(exc))

        for price, label in (
            (order.entry_price, "Entry price"),
            (order.stop_loss, "Stop loss"),
            (order.take_profit, "Take profit"),
        ):
            try:
                validate_price(price, label)
            except ValueError as exc:
                errors.append(str(exc))

        normalized_type = order.order_type.strip().upper() if order.order_type else ""
        if normalized_type in {"LIMIT", "STOP"} and order.entry_price is None:
            errors.append("Entry price is required for LIMIT and STOP orders.")

        if order.stop_loss is None:
            warnings.append("Stop loss is not provided.")
        if order.take_profit is None:
            warnings.append("Take profit is not provided.")

        return OrderValidationResult(valid=not errors, errors=errors, warnings=warnings)

