from typing import Any

from backend.demo_execution.demo_execution_models import DemoExecutionRequest, DemoExecutionResult
from backend.demo_execution.mt5_demo_execution_guard import MT5DemoExecutionGuard
from backend.demo_execution.mt5_demo_order_builder import MT5DemoOrderBuilder
from backend.execution_queue.execution_queue_models import ExecutionQueueItem


class MT5DemoExecutor:
    """Execute one tiny MT5 demo order only after all demo guards pass."""

    def __init__(
        self,
        guard: MT5DemoExecutionGuard | None = None,
        order_builder: MT5DemoOrderBuilder | None = None,
    ) -> None:
        self.guard = guard or MT5DemoExecutionGuard()
        self.order_builder = order_builder or MT5DemoOrderBuilder(self.guard.account_verifier.connection_manager.mt5)

    def execute_demo_order(
        self,
        queue_item: ExecutionQueueItem | None,
        request: DemoExecutionRequest,
    ) -> DemoExecutionResult:
        allowed, reasons, account_status = self.guard.validate_demo_execution(queue_item, request)
        if not allowed or queue_item is None:
            status = "MT5_UNAVAILABLE" if not account_status.terminal_available else "BLOCKED"
            return self._result(queue_item, request.queue_id, status, reasons)

        try:
            self.order_builder.mt5 = self.guard.account_verifier.connection_manager.mt5
            order_request = self.order_builder.build_market_order(queue_item.intent)
            mt5 = self.guard.account_verifier.connection_manager.mt5
            if mt5 is None:
                return self._result(queue_item, request.queue_id, "MT5_UNAVAILABLE", ["MT5 module unavailable."])

            # The only allowed MT5 submission point: guarded, demo-only, EURUSD, max 0.01 lot.
            result = mt5.order_send(order_request)
            retcode = getattr(result, "retcode", None)
            order = getattr(result, "order", None)
            deal = getattr(result, "deal", None)
            filled = self._is_success_retcode(mt5, retcode)
            return self._result(
                queue_item,
                request.queue_id,
                "DEMO_FILLED" if filled else "DEMO_REJECTED",
                [] if filled else [str(getattr(result, "comment", "MT5 demo order rejected."))],
                mt5_retcode=retcode,
                mt5_order=order,
                mt5_deal=deal,
                executed_lot=queue_item.intent.allocated_lot if filled else 0.0,
            )
        except Exception as exc:
            return self._result(queue_item, request.queue_id, "FAILED_SAFE", [f"Demo execution failed safely: {exc}"])

    def _is_success_retcode(self, mt5: Any, retcode: Any) -> bool:
        success_codes = {
            getattr(mt5, "TRADE_RETCODE_DONE", None),
            getattr(mt5, "TRADE_RETCODE_PLACED", None),
        }
        return retcode in {code for code in success_codes if code is not None}

    def _result(
        self,
        queue_item: ExecutionQueueItem | None,
        queue_id: str,
        status: str,
        rejection_reasons: list[str],
        mt5_retcode: int | str | None = None,
        mt5_order: int | str | None = None,
        mt5_deal: int | str | None = None,
        executed_lot: float = 0.0,
    ) -> DemoExecutionResult:
        intent = queue_item.intent if queue_item is not None else None
        return DemoExecutionResult(
            queue_id=queue_id,
            broker_id=getattr(intent, "broker_id", None),
            account_id=getattr(intent, "account_id", None),
            canonical_symbol=getattr(intent, "canonical_symbol", None),
            broker_symbol=getattr(intent, "broker_symbol", None) or getattr(intent, "canonical_symbol", None),
            action=getattr(intent, "action", None),
            requested_lot=float(getattr(intent, "allocated_lot", 0.0) or 0.0),
            executed_lot=executed_lot,
            order_type=getattr(intent, "order_type", "MARKET"),
            mt5_retcode=mt5_retcode,
            mt5_order=mt5_order,
            mt5_deal=mt5_deal,
            status=status,
            rejection_reasons=rejection_reasons,
            warnings=["Demo execution bridge only. Live execution remains disabled."],
            demo_execution=True,
            live_execution_enabled=False,
        )
