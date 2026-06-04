from backend.nifty50.nifty_execution_models import NIFTYExecutionIntent, NIFTYOrderPreview
from backend.nifty50.nifty_execution_validator import NIFTYExecutionValidator


class NIFTYBrokerOrderPreview:
    def __init__(self, validator: NIFTYExecutionValidator | None = None) -> None:
        self.validator = validator or NIFTYExecutionValidator()

    def create_preview(self, intent: NIFTYExecutionIntent) -> NIFTYOrderPreview:
        reasons = self.validator.validate_intent(intent)
        if "Broker not selected." in reasons:
            status = "BROKER_NOT_SELECTED"
        elif "Execution disabled; preview only." in reasons or "Broker execution disabled." in reasons:
            status = "BLOCKED_EXECUTION_DISABLED"
        elif reasons:
            status = "REJECTED"
        else:
            status = "READY_FOR_REVIEW"
        estimated_value = float(max(intent.quantity, 0) * 1)
        return NIFTYOrderPreview(
            intent_id=intent.intent_id,
            broker_id=intent.broker_id,
            symbol=intent.symbol,
            exchange=intent.exchange,
            action=intent.action,
            quantity=intent.quantity,
            order_type=intent.order_type,
            product_type=intent.product_type,
            estimated_value=estimated_value,
            charges_placeholder=0.0,
            margin_required_placeholder=0.0,
            preview_status=status,
            rejection_reasons=reasons,
        )
