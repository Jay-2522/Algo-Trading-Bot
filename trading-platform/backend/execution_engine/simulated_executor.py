from datetime import datetime, timezone
from uuid import uuid4

from backend.execution_engine.execution_models import ExecutionResult, OrderRequest


class SimulatedExecutor:
    """Fill validated requests in memory only; no broker connection is used."""

    def execute(self, order: OrderRequest) -> ExecutionResult:
        return ExecutionResult(
            success=True,
            execution_id=str(uuid4()),
            symbol=order.symbol.strip().upper(),
            side=order.side.strip().upper(),
            lot_size=order.lot_size,
            execution_mode="SIMULATION",
            status="SIMULATED_FILLED",
            message="Order filled in simulation mode only. No broker order was submitted.",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

