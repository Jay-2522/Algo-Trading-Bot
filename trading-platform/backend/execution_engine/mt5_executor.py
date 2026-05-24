from datetime import datetime, timezone
from uuid import uuid4

from backend.execution_engine.execution_models import ExecutionResult, OrderRequest


class MT5Executor:
    """Preview future MT5 payloads while live execution remains disabled."""

    def prepare_order_payload(self, order: OrderRequest) -> dict:
        """Return a JSON-safe MT5 payload preview without sending an order."""

        return {
            "symbol": order.symbol.strip().upper(),
            "side": order.side.strip().upper(),
            "order_type": order.order_type.strip().upper(),
            "volume": order.lot_size,
            "price": order.entry_price,
            "stop_loss": order.stop_loss,
            "take_profit": order.take_profit,
            "comment": order.comment,
            "preview_only": True,
            "real_execution_enabled": False,
        }

    def execute(self, order: OrderRequest) -> ExecutionResult:
        """Return a disabled result; no broker submission is implemented."""

        return ExecutionResult(
            success=False,
            execution_id=str(uuid4()),
            symbol=order.symbol.strip().upper(),
            side=order.side.strip().upper(),
            lot_size=order.lot_size,
            execution_mode="MT5_DISABLED",
            status="REAL_EXECUTION_DISABLED",
            message="Real MT5 execution is disabled in Day 5 foundation.",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
