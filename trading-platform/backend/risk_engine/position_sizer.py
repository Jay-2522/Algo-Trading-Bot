from backend.risk_engine.risk_models import PositionSizeResponse
from backend.risk_engine.validators import validate_positive_number, validate_risk_percent


class PositionSizer:
    """Calculate risk-sized lots without creating or transmitting an order."""

    def calculate_lot_size(
        self,
        account_balance: float,
        risk_percent: float,
        stop_loss_pips: float,
        pip_value: float,
    ) -> PositionSizeResponse:
        """Return lot size derived from balance, risk percentage, and stop size."""

        validate_positive_number(account_balance, "Account balance")
        validate_risk_percent(risk_percent)
        validate_positive_number(stop_loss_pips, "Stop loss pips")
        validate_positive_number(pip_value, "Pip value")

        risk_amount = account_balance * (risk_percent / 100)
        lot_size = risk_amount / (stop_loss_pips * pip_value)
        return PositionSizeResponse(
            lot_size=round(lot_size, 2),
            risk_amount=round(risk_amount, 2),
            stop_loss_pips=stop_loss_pips,
            status="calculated",
        )

