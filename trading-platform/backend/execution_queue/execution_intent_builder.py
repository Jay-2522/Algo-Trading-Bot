from typing import Any

from backend.account_routing.allocation_models import AllocationDecision, LotAllocation
from backend.broker_compatibility.broker_symbol_mapper import BrokerSymbolMapper
from backend.execution_queue.execution_queue_models import ExecutionIntent


class ExecutionIntentBuilder:
    """Build non-executing execution intents from approved allocation decisions."""

    APPROVED_STATUSES = {"APPROVED", "REDUCED"}

    def __init__(self, symbol_mapper: BrokerSymbolMapper | None = None) -> None:
        self.symbol_mapper = symbol_mapper or BrokerSymbolMapper()

    def build_intents_from_allocation(
        self,
        allocation_decision: AllocationDecision,
        signal_payload: dict[str, Any] | None = None,
    ) -> list[ExecutionIntent]:
        signal_payload = signal_payload or {}
        intents: list[ExecutionIntent] = []
        if not allocation_decision.routing_ready:
            return intents
        for allocation in allocation_decision.allocations:
            if allocation.allocation_status not in self.APPROVED_STATUSES:
                continue
            intents.append(self._intent_from_allocation(allocation_decision, allocation, signal_payload))
        return intents

    def _intent_from_allocation(
        self,
        decision: AllocationDecision,
        allocation: LotAllocation,
        signal_payload: dict[str, Any],
    ) -> ExecutionIntent:
        mapping = self.symbol_mapper.map_symbol(allocation.broker_id, allocation.canonical_symbol)
        return ExecutionIntent(
            signal_id=decision.signal_id,
            account_id=allocation.account_id,
            broker_id=allocation.broker_id,
            canonical_symbol=allocation.canonical_symbol,
            broker_symbol=mapping.broker_symbol or allocation.canonical_symbol,
            action=allocation.action,
            allocated_lot=allocation.allocated_lot,
            order_type=str(signal_payload.get("order_type") or "MARKET").upper(),
            requested_price=signal_payload.get("requested_price") or signal_payload.get("price"),
            stop_loss=signal_payload.get("stop_loss"),
            take_profit=signal_payload.get("take_profit"),
            source="ALLOCATION_PREVIEW",
            simulation_only=True,
            live_execution_enabled=False,
        )
