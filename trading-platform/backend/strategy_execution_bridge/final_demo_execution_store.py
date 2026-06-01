from backend.strategy_execution_bridge.final_demo_execution_models import FinalDemoExecutionDecision


class FinalDemoExecutionStore:
    """In-memory audit store for final demo execution decisions."""

    _decisions: dict[str, FinalDemoExecutionDecision] = {}

    def store_decision(self, decision: FinalDemoExecutionDecision) -> FinalDemoExecutionDecision:
        self._decisions[decision.final_execution_id] = decision
        return decision

    def list_decisions(self, limit: int = 100) -> list[FinalDemoExecutionDecision]:
        return sorted(self._decisions.values(), key=lambda decision: decision.timestamp, reverse=True)[:limit]

    def get_decision(self, final_execution_id: str) -> FinalDemoExecutionDecision | None:
        return self._decisions.get(final_execution_id)

    def get_by_candidate_id(self, candidate_id: str) -> FinalDemoExecutionDecision | None:
        executions = [
            decision
            for decision in self._decisions.values()
            if decision.candidate_id == candidate_id
            and decision.execution_status
            not in {
                "BLOCKED_NOT_CONFIRMED",
                "BLOCKED_CANDIDATE_NOT_FOUND",
                "BLOCKED_CANDIDATE_NOT_APPROVED",
                "BLOCKED_STALE_CANDIDATE",
                "BLOCKED_RISK_ENGINE",
                "FAILED_SAFE",
            }
        ]
        return sorted(executions, key=lambda decision: decision.timestamp, reverse=True)[0] if executions else None

    def has_executed_candidate(self, candidate_id: str) -> bool:
        return self.get_by_candidate_id(candidate_id) is not None
