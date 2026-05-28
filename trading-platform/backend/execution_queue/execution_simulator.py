from backend.execution_queue.execution_lifecycle_models import SimulatedExecutionResult
from backend.execution_queue.execution_queue_models import ExecutionQueueItem


class ExecutionSimulator:
    """Emulate execution lifecycle outcomes without broker order placement."""

    VALID_ACTIONS = {"BUY", "SELL", "CLOSE"}

    def simulate_execution(self, queue_item: ExecutionQueueItem) -> SimulatedExecutionResult:
        intent = queue_item.intent
        rejection = self._rejection_reason(queue_item)
        if rejection:
            return SimulatedExecutionResult(
                queue_id=queue_item.queue_id,
                account_id=intent.account_id,
                broker_id=intent.broker_id,
                canonical_symbol=intent.canonical_symbol,
                action=str(intent.action),
                requested_lot=intent.allocated_lot,
                filled_lot=0.0,
                requested_price=intent.requested_price,
                simulated_fill_price=None,
                status="SIMULATION_BLOCKED" if "live execution" in rejection.lower() else "SIMULATED_REJECTED",
                rejection_reason=rejection,
                slippage_points=0.0,
                simulation_only=True,
                live_execution_enabled=False,
            )

        slippage = self._deterministic_slippage(intent.canonical_symbol, intent.action)
        requested_price = intent.requested_price or self._safe_price(intent.canonical_symbol)
        fill_price = requested_price + slippage if intent.action == "BUY" else requested_price - slippage
        return SimulatedExecutionResult(
            queue_id=queue_item.queue_id,
            account_id=intent.account_id,
            broker_id=intent.broker_id,
            canonical_symbol=intent.canonical_symbol,
            action=intent.action,
            requested_lot=intent.allocated_lot,
            filled_lot=intent.allocated_lot,
            requested_price=requested_price,
            simulated_fill_price=round(fill_price, 5 if intent.canonical_symbol == "EURUSD" else 2),
            status="SIMULATED_FILLED",
            rejection_reason=None,
            slippage_points=slippage,
            simulation_only=True,
            live_execution_enabled=False,
        )

    def _rejection_reason(self, queue_item: ExecutionQueueItem) -> str | None:
        intent = queue_item.intent
        if queue_item.status == "CANCELLED":
            return "Queue item has been cancelled."
        if queue_item.readiness != "READY_FOR_DEMO_QUEUE":
            return "Queue item is not ready for demo queue simulation."
        if intent.allocated_lot <= 0:
            return "Allocated lot must be greater than zero."
        if intent.action not in self.VALID_ACTIONS:
            return "Intent action is invalid."
        if intent.live_execution_enabled or queue_item.live_execution_enabled:
            return "Live execution must remain disabled."
        return None

    def _safe_price(self, symbol: str) -> float:
        if symbol == "EURUSD":
            return 1.085
        if symbol == "XAUUSD":
            return 2400.0
        return 100.0

    def _deterministic_slippage(self, symbol: str, action: str) -> float:
        seed = (sum(ord(char) for char in f"{symbol}:{action}") % 3) + 1
        if symbol == "EURUSD":
            return round(seed * 0.00001, 5)
        if symbol == "XAUUSD":
            return round(seed * 0.05, 2)
        return round(seed * 0.01, 2)
