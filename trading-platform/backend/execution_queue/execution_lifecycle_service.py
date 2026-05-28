from backend.execution_queue.execution_audit_logger import ExecutionAuditLogger
from backend.execution_queue.execution_lifecycle_models import (
    ExecutionAuditEvent,
    OrderLifecycleState,
    SimulatedExecutionResult,
)
from backend.execution_queue.execution_queue_manager import ExecutionQueueManager
from backend.execution_queue.execution_reconciliation_engine import ExecutionReconciliationEngine
from backend.execution_queue.execution_simulator import ExecutionSimulator
from backend.execution_queue.order_lifecycle_tracker import OrderLifecycleTracker


class ExecutionLifecycleService:
    """Simulate queue item execution lifecycle without broker execution."""

    def __init__(
        self,
        queue_manager: ExecutionQueueManager,
        simulator: ExecutionSimulator | None = None,
        tracker: OrderLifecycleTracker | None = None,
        audit_logger: ExecutionAuditLogger | None = None,
        reconciliation_engine: ExecutionReconciliationEngine | None = None,
    ) -> None:
        self.queue_manager = queue_manager
        self.simulator = simulator or ExecutionSimulator()
        self.tracker = tracker or OrderLifecycleTracker()
        self.audit_logger = audit_logger or ExecutionAuditLogger()
        self.reconciliation_engine = reconciliation_engine or ExecutionReconciliationEngine()
        self.results: dict[str, SimulatedExecutionResult] = {}

    def get_status(self) -> dict:
        lifecycles = self.tracker.list_lifecycles()
        return {
            "status": "operational",
            "mode": "SIMULATED_EXECUTION_LIFECYCLE_ONLY",
            "lifecycles": len(lifecycles),
            "audit_events": len(self.audit_logger.get_events(1000)),
            "simulation_only": True,
            "live_execution_enabled": False,
        }

    def simulate_queue_item(self, queue_id: str) -> SimulatedExecutionResult | None:
        queue_item = self.queue_manager.get_item(queue_id)
        if queue_item is None:
            return None
        lifecycle = self.tracker.get_lifecycle(queue_id) or self.tracker.create_lifecycle(queue_item)
        self.audit_logger.log_event(queue_id, "LIFECYCLE_CREATED", "Simulation lifecycle started.")
        if queue_item.readiness == "READY_FOR_DEMO_QUEUE":
            self.tracker.update_state(queue_id, "VALIDATED", "Queue item passed simulation readiness validation.")
            self.tracker.update_state(queue_id, "SIMULATED_ACCEPTED", "Queue item accepted by simulated execution engine.")
        result = self.simulator.simulate_execution(queue_item)
        lifecycle.execution_id = result.execution_id
        if result.status == "SIMULATED_FILLED":
            self.tracker.update_state(queue_id, "SIMULATED_FILLED", "Queue item filled by simulator.")
        elif result.status == "SIMULATED_CANCELLED":
            self.tracker.update_state(queue_id, "CANCELLED", "Queue item cancelled in simulator.")
        elif result.status == "SIMULATED_REJECTED":
            self.tracker.update_state(queue_id, "SIMULATED_REJECTED", result.rejection_reason or "Simulated rejection.")
        else:
            self.tracker.update_state(queue_id, "FAILED_SAFE", result.rejection_reason or "Simulation blocked.")
        reconciliation = self.reconciliation_engine.reconcile_simulated_execution(result)
        self.audit_logger.log_event(
            queue_id,
            result.status,
            result.rejection_reason or "Simulated execution result created.",
            {"execution_id": result.execution_id, "reconciliation": reconciliation},
        )
        self.results[queue_id] = result
        return result

    def simulate_latest(self) -> SimulatedExecutionResult | None:
        for item in self.queue_manager.list_queue(1000):
            if item.status == "QUEUED":
                return self.simulate_queue_item(item.queue_id)
        return None

    def get_lifecycles(self) -> list[OrderLifecycleState]:
        return self.tracker.list_lifecycles()

    def get_audit_events(self, limit: int = 100) -> list[ExecutionAuditEvent]:
        return self.audit_logger.get_events(limit)
