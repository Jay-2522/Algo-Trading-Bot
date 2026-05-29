from typing import Any

from backend.demo_execution.demo_execution_models import DemoExecutionRequest, DemoExecutionResult, MT5DemoAccountStatus
from backend.demo_execution.demo_execution_result_store import DemoExecutionResultStore
from backend.demo_execution.mt5_demo_account_verifier import MT5DemoAccountVerifier
from backend.demo_execution.mt5_demo_execution_guard import MT5DemoExecutionGuard
from backend.demo_execution.mt5_demo_executor import MT5DemoExecutor
from backend.execution_queue.execution_lifecycle_models import ExecutionAuditEvent
from backend.execution_queue.execution_queue_models import ExecutionQueueItem
from backend.execution_queue.execution_queue_service import ExecutionQueueService


class DemoExecutionService:
    """Facade for guarded MT5 demo execution from queue items."""

    def __init__(
        self,
        execution_queue_service: ExecutionQueueService | None = None,
        account_verifier: MT5DemoAccountVerifier | None = None,
        executor: MT5DemoExecutor | None = None,
        result_store: DemoExecutionResultStore | None = None,
        safety_service: Any | None = None,
    ) -> None:
        self.execution_queue_service = execution_queue_service or ExecutionQueueService()
        self.account_verifier = account_verifier or MT5DemoAccountVerifier()
        self.result_store = result_store or DemoExecutionResultStore()
        self.safety_service = safety_service
        self.executor = executor or MT5DemoExecutor(
            guard=MT5DemoExecutionGuard(
                account_verifier=self.account_verifier,
                control_center_service=safety_service,
            )
        )

    def get_status(self) -> dict[str, Any]:
        account_status = self.verify_account()
        return {
            "status": "DEMO_EXECUTION_READY" if account_status.demo_execution_allowed else "DEMO_EXECUTION_BLOCKED",
            "mode": "MT5_DEMO_EXECUTION_ONLY",
            "demo_execution_enabled": True,
            "allowed_symbol": "EURUSD",
            "max_lot": 0.01,
            "market_orders_only": True,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "account": account_status.model_dump(mode="json"),
        }

    def verify_account(self) -> MT5DemoAccountStatus:
        return self.account_verifier.verify_demo_account()

    def execute_queue_item_demo(self, queue_id: str, request: DemoExecutionRequest | dict[str, Any]) -> DemoExecutionResult:
        parsed_request = request if isinstance(request, DemoExecutionRequest) else DemoExecutionRequest(queue_id=queue_id, **request)
        item = self.execution_queue_service.get_item(queue_id)
        if self.result_store.has_queue_execution(queue_id):
            result = self._blocked_result(item, queue_id, ["Queue item has already been submitted to the demo execution flow."])
            self._record_blocked(queue_id, result.rejection_reasons)
            return self.result_store.store_result(result)

        self._ensure_lifecycle(item, queue_id)
        self._log_event(queue_id, "DEMO_EXECUTION_REQUESTED", parsed_request.reason or "Demo execution requested.", {
            "requested_by": parsed_request.requested_by,
            "confirm_demo_execution": parsed_request.confirm_demo_execution,
            "simulation_only": True,
            "live_execution_enabled": False,
        })
        result = self.executor.execute_demo_order(item, parsed_request)
        self._apply_lifecycle_result(queue_id, result)
        self._log_result_event(result)
        return self.result_store.store_result(result)

    def execute_latest_eligible(self, request: DemoExecutionRequest | dict[str, Any]) -> DemoExecutionResult:
        eligible = self.get_eligible_queue_items()
        if not eligible:
            parsed_request = self._latest_request(request, "latest")
            result = DemoExecutionResult(
                queue_id=parsed_request.queue_id,
                status="BLOCKED",
                rejection_reasons=["No eligible EURUSD demo queue item is available."],
                warnings=["Demo execution bridge only. Live execution remains disabled."],
                demo_execution=True,
                simulation_only=True,
                live_execution_enabled=False,
                broker_execution_enabled=False,
            )
            self._record_blocked(parsed_request.queue_id, result.rejection_reasons)
            return self.result_store.store_result(result)
        item = eligible[0]
        parsed_request = self._latest_request(request, item.queue_id)
        return self.execute_queue_item_demo(item.queue_id, parsed_request)

    def get_eligible_queue_items(self, limit: int = 100) -> list[ExecutionQueueItem]:
        safety = self._get_safety_state()
        if safety.get("queue_paused") or safety.get("emergency_stop_active"):
            return []
        eligible: list[ExecutionQueueItem] = []
        for item in self.execution_queue_service.list_items(1000):
            if len(eligible) >= limit:
                break
            if self._is_eligible(item):
                eligible.append(item)
        return eligible

    def list_results(self, limit: int = 100) -> list[DemoExecutionResult]:
        return self.result_store.list_results(limit)

    def get_result(self, execution_id: str) -> DemoExecutionResult | None:
        return self.result_store.get_result(execution_id)

    def get_audit_events(self, limit: int = 100) -> list[ExecutionAuditEvent]:
        return self.execution_queue_service.get_audit_events(limit)

    def _is_eligible(self, item: ExecutionQueueItem) -> bool:
        intent = item.intent
        return (
            item.status == "QUEUED"
            and item.readiness == "READY_FOR_DEMO_QUEUE"
            and not self.result_store.has_queue_execution(item.queue_id)
            and intent.canonical_symbol == "EURUSD"
            and intent.action in {"BUY", "SELL"}
            and intent.order_type == "MARKET"
            and float(intent.allocated_lot or 0.0) <= 0.01
            and item.live_execution_enabled is False
            and intent.live_execution_enabled is False
        )

    def _get_safety_state(self) -> dict[str, Any]:
        if self.safety_service is None:
            return {"queue_paused": False, "emergency_stop_active": False}
        try:
            state = self.safety_service.get_safety_state()
            if hasattr(state, "model_dump"):
                return state.model_dump(mode="json")
            if isinstance(state, dict):
                return state
        except Exception:
            return {"queue_paused": False, "emergency_stop_active": False}
        return {"queue_paused": False, "emergency_stop_active": False}

    def _latest_request(self, request: DemoExecutionRequest | dict[str, Any], queue_id: str) -> DemoExecutionRequest:
        if isinstance(request, DemoExecutionRequest):
            data = request.model_dump()
        else:
            data = dict(request)
        data.pop("queue_id", None)
        return DemoExecutionRequest(queue_id=queue_id, **data)

    def _ensure_lifecycle(self, item: ExecutionQueueItem | None, queue_id: str) -> None:
        tracker = self.execution_queue_service.lifecycle_service.tracker
        if item is not None and tracker.get_lifecycle(queue_id) is None:
            tracker.create_lifecycle(item)
        tracker.update_state(queue_id, "VALIDATED", "Queue item entered guarded MT5 demo execution validation.")

    def _apply_lifecycle_result(self, queue_id: str, result: DemoExecutionResult) -> None:
        tracker = self.execution_queue_service.lifecycle_service.tracker
        if result.status == "DEMO_FILLED":
            tracker.update_state(queue_id, "DEMO_ORDER_SENT", "Guarded MT5 demo order was sent.")
            tracker.update_state(queue_id, "DEMO_FILLED", "MT5 demo order returned a filled status.")
        elif result.status == "DEMO_REJECTED":
            tracker.update_state(queue_id, "DEMO_ORDER_SENT", "Guarded MT5 demo order was sent.")
            tracker.update_state(queue_id, "DEMO_REJECTED", "; ".join(result.rejection_reasons) or "MT5 demo order rejected.")
        else:
            tracker.update_state(queue_id, "FAILED_SAFE", "; ".join(result.rejection_reasons) or "Demo execution blocked safely.")

    def _blocked_result(self, item: ExecutionQueueItem | None, queue_id: str, reasons: list[str]) -> DemoExecutionResult:
        intent = item.intent if item is not None else None
        return DemoExecutionResult(
            queue_id=queue_id,
            broker_id=getattr(intent, "broker_id", None),
            account_id=getattr(intent, "account_id", None),
            canonical_symbol=getattr(intent, "canonical_symbol", None),
            broker_symbol=getattr(intent, "broker_symbol", None) or getattr(intent, "canonical_symbol", None),
            action=getattr(intent, "action", None),
            requested_lot=float(getattr(intent, "allocated_lot", 0.0) or 0.0),
            status="BLOCKED",
            rejection_reasons=reasons,
            warnings=["Demo execution bridge only. Live execution remains disabled."],
            demo_execution=True,
            simulation_only=True,
            live_execution_enabled=False,
            broker_execution_enabled=False,
        )

    def _record_blocked(self, queue_id: str, reasons: list[str]) -> None:
        self.execution_queue_service.lifecycle_service.tracker.update_state(
            queue_id,
            "FAILED_SAFE",
            "; ".join(reasons) or "Demo execution blocked safely.",
        )
        self._log_event(queue_id, "DEMO_EXECUTION_BLOCKED", "; ".join(reasons) or "Demo execution blocked safely.")

    def _log_result_event(self, result: DemoExecutionResult) -> None:
        if result.status == "DEMO_FILLED":
            self._log_event(result.queue_id, "DEMO_ORDER_SENT", "Guarded MT5 demo order was sent.", result.model_dump(mode="json"))
            self._log_event(result.queue_id, "DEMO_EXECUTION_FILLED", "MT5 demo execution filled.", result.model_dump(mode="json"))
        elif result.status == "DEMO_REJECTED":
            self._log_event(result.queue_id, "DEMO_ORDER_SENT", "Guarded MT5 demo order was sent.", result.model_dump(mode="json"))
            self._log_event(result.queue_id, "DEMO_EXECUTION_REJECTED", "MT5 demo execution rejected.", result.model_dump(mode="json"))
        elif result.status == "FAILED_SAFE":
            self._log_event(result.queue_id, "DEMO_EXECUTION_FAILED_SAFE", "MT5 demo execution failed safely.", result.model_dump(mode="json"))
        elif result.status == "MT5_UNAVAILABLE":
            self._log_event(result.queue_id, "DEMO_EXECUTION_BLOCKED", "MT5 unavailable for guarded demo execution.", result.model_dump(mode="json"))
        else:
            self._log_event(result.queue_id, "DEMO_EXECUTION_BLOCKED", "Demo execution blocked safely.", result.model_dump(mode="json"))

    def _log_event(
        self,
        queue_id: str,
        event_type: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.execution_queue_service.lifecycle_service.audit_logger.log_event(
            queue_id,
            event_type,
            message,
            metadata or {"simulation_only": True, "live_execution_enabled": False},
        )
