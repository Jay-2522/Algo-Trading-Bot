from backend.account_routing.account_registry import AccountRegistry
from backend.broker_compatibility.broker_registry import BrokerRegistry
from backend.execution_queue.execution_queue_models import ExecutionIntent
from backend.replay.client_symbol_registry import ClientSymbolRegistry


class ExecutionReadinessValidator:
    """Validate execution intents for demo queue readiness without execution."""

    VALID_ACTIONS = {"BUY", "SELL", "CLOSE"}

    def __init__(
        self,
        account_registry: AccountRegistry | None = None,
        broker_registry: BrokerRegistry | None = None,
        symbol_registry: ClientSymbolRegistry | None = None,
    ) -> None:
        self.account_registry = account_registry or AccountRegistry()
        self.broker_registry = broker_registry or BrokerRegistry()
        self.symbol_registry = symbol_registry or ClientSymbolRegistry()

    def validate_intent(self, intent: ExecutionIntent) -> tuple[str, list[str], list[str]]:
        errors: list[str] = []
        warnings: list[str] = []
        account = self.account_registry.get_account(intent.account_id)
        if account is None:
            errors.append("Account profile does not exist.")
        elif not account.enabled:
            errors.append("Account is disabled.")
        if not self.broker_registry.is_supported_broker(intent.broker_id):
            errors.append("Broker is not supported.")
        if not self.symbol_registry.is_supported(intent.canonical_symbol):
            errors.append("Symbol is not supported.")
        if intent.allocated_lot <= 0:
            errors.append("Allocated lot must be greater than zero.")
        if intent.action not in self.VALID_ACTIONS:
            errors.append("Intent action is invalid.")
        if intent.live_execution_enabled:
            errors.append("Live execution flag must remain disabled.")
        if intent.simulation_only is not True:
            errors.append("Intent must be simulation-only.")
        if intent.order_type == "NONE":
            warnings.append("Order type is NONE; intent is held for confirmation.")
        if errors:
            return "INVALID", errors, warnings
        if warnings:
            return "WAITING_FOR_CONFIRMATION", errors, warnings
        return "READY_FOR_DEMO_QUEUE", errors, warnings
