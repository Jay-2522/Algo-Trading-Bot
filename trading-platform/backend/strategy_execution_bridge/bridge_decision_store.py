from backend.strategy_execution_bridge.bridge_models import StrategyBridgeDecision


class BridgeDecisionStore:
    """In-memory audit store for strategy execution bridge decisions."""

    _decisions: dict[str, StrategyBridgeDecision] = {}

    def store_decision(self, decision: StrategyBridgeDecision) -> StrategyBridgeDecision:
        self._decisions[decision.decision_id] = decision
        return decision

    def list_decisions(self, limit: int = 100) -> list[StrategyBridgeDecision]:
        return sorted(self._decisions.values(), key=lambda decision: decision.timestamp, reverse=True)[:limit]

    def get_decision(self, decision_id: str) -> StrategyBridgeDecision | None:
        return self._decisions.get(decision_id)
