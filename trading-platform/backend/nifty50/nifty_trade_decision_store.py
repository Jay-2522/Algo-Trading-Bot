from backend.nifty50.nifty_risk_models import NIFTYRiskDecision, NIFTYTradeCandidate


class NIFTYTradeDecisionStore:
    def __init__(self) -> None:
        self._decisions: list[NIFTYRiskDecision] = []
        self._candidates: list[NIFTYTradeCandidate] = []

    def store_decision(self, decision: NIFTYRiskDecision) -> NIFTYRiskDecision:
        self._decisions.append(decision)
        return decision

    def list_decisions(self, limit: int = 100) -> list[NIFTYRiskDecision]:
        return self._decisions[-limit:]

    def get_decision(self, decision_id: str) -> NIFTYRiskDecision | None:
        return next((decision for decision in self._decisions if decision.decision_id == decision_id), None)

    def store_candidate(self, candidate: NIFTYTradeCandidate) -> NIFTYTradeCandidate:
        self._candidates.append(candidate)
        return candidate

    def list_candidates(self, limit: int = 100) -> list[NIFTYTradeCandidate]:
        return self._candidates[-limit:]
