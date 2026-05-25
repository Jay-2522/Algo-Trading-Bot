from backend.orchestration.decision_coordinator import DecisionCoordinator
from backend.orchestration.orchestration_logger import OrchestrationLogger
from backend.orchestration.orchestration_models import OrchestrationDecision, PipelineResult
from backend.orchestration.pipeline_runner import PipelineRunner
from backend.orchestration.symbol_monitor import SymbolMonitor


class OrchestratorService:
    """Coordinate one-shot trading-readiness pipelines with simulation-only execution."""

    def __init__(
        self,
        pipeline_runner: PipelineRunner | None = None,
        decision_coordinator: DecisionCoordinator | None = None,
        symbol_monitor: SymbolMonitor | None = None,
        orchestration_logger: OrchestrationLogger | None = None,
    ) -> None:
        self.pipeline_runner = pipeline_runner or PipelineRunner()
        self.decision_coordinator = decision_coordinator or DecisionCoordinator()
        self.symbol_monitor = symbol_monitor or SymbolMonitor()
        self.orchestration_logger = orchestration_logger or OrchestrationLogger()
        self._last_decisions: dict[str, OrchestrationDecision] = {}

    def run_symbol_pipeline(self, symbol: str, timeframe: str = "M15") -> PipelineResult:
        context, steps_run = self.pipeline_runner.collect_context(symbol, timeframe)
        decision = self.decision_coordinator.create_final_decision(context)

        if decision.approved:
            execution_result = self.pipeline_runner.simulate_if_approved(context, decision)
            steps_run.append("optionally_simulate_execution")
            if not execution_result or not execution_result.get("success", False):
                message = (execution_result or {}).get(
                    "message",
                    "Simulation validation failed after advisory approval.",
                )
                decision = self.decision_coordinator.block_after_execution_validation(decision, message)

        result = PipelineResult(
            success=True,
            symbol=context.symbol,
            decision=decision,
            steps_run=steps_run,
            errors=context.errors,
        )
        self._last_decisions[context.symbol] = decision
        context.metadata["persistence"] = self.orchestration_logger.log_pipeline_result(result)
        return result

    def get_orchestration_status(self) -> dict:
        return {
            "status": "operational",
            "mode": "SIMULATION_ONLY",
            "live_execution_enabled": False,
            "background_loop_enabled": False,
            "monitored_symbols": self.symbol_monitor.get_symbols(),
        }

    def get_monitored_symbols(self) -> list[str]:
        return self.symbol_monitor.get_symbols()

    def add_monitored_symbol(self, symbol: str) -> list[str]:
        return self.symbol_monitor.add_symbol(symbol)

    def remove_monitored_symbol(self, symbol: str) -> list[str]:
        return self.symbol_monitor.remove_symbol(symbol)

    def get_last_decision(self, symbol: str) -> OrchestrationDecision | None:
        return self._last_decisions.get(symbol.strip().upper())
