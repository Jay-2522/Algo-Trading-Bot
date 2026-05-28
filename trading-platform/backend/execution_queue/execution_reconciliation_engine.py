from backend.execution_queue.execution_lifecycle_models import SimulatedExecutionResult


class ExecutionReconciliationEngine:
    """Reconcile simulated execution results for dashboard/audit summaries."""

    def reconcile_simulated_execution(self, execution_result: SimulatedExecutionResult) -> dict:
        if execution_result.status != "SIMULATED_FILLED":
            return {
                "reconciled": False,
                "status": execution_result.status,
                "message": execution_result.rejection_reason or "Execution was not filled.",
                "simulation_only": True,
                "live_execution_enabled": False,
            }
        matched = round(execution_result.filled_lot, 8) == round(execution_result.requested_lot, 8)
        return {
            "reconciled": matched,
            "status": execution_result.status,
            "requested_lot": execution_result.requested_lot,
            "filled_lot": execution_result.filled_lot,
            "message": "Simulated fill reconciled." if matched else "Simulated fill lot mismatch detected.",
            "simulation_only": True,
            "live_execution_enabled": False,
        }
