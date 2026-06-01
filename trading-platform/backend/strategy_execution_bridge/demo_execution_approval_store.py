from backend.strategy_execution_bridge.demo_approval_models import (
    DemoExecutionApprovalDecision,
    DemoExecutionCandidate,
)


class DemoExecutionApprovalStore:
    """In-memory approval and candidate store for demo execution approvals."""

    _approvals: dict[str, DemoExecutionApprovalDecision] = {}
    _candidates: dict[str, DemoExecutionCandidate] = {}

    def store_approval(self, approval: DemoExecutionApprovalDecision) -> DemoExecutionApprovalDecision:
        self._approvals[approval.approval_id] = approval
        return approval

    def list_approvals(self, limit: int = 100) -> list[DemoExecutionApprovalDecision]:
        return sorted(self._approvals.values(), key=lambda approval: approval.timestamp, reverse=True)[:limit]

    def get_approval(self, approval_id: str) -> DemoExecutionApprovalDecision | None:
        return self._approvals.get(approval_id)

    def get_by_decision_id(self, decision_id: str) -> DemoExecutionApprovalDecision | None:
        approvals = [
            approval
            for approval in self._approvals.values()
            if approval.decision_id == decision_id and approval.approved
        ]
        return sorted(approvals, key=lambda approval: approval.timestamp, reverse=True)[0] if approvals else None

    def has_existing_approval(self, decision_id: str) -> bool:
        return self.get_by_decision_id(decision_id) is not None

    def store_candidate(self, candidate: DemoExecutionCandidate) -> DemoExecutionCandidate:
        self._candidates[candidate.candidate_id] = candidate
        return candidate

    def list_candidates(self, limit: int = 100) -> list[DemoExecutionCandidate]:
        return sorted(self._candidates.values(), key=lambda candidate: candidate.timestamp, reverse=True)[:limit]

    def get_candidate(self, candidate_id: str) -> DemoExecutionCandidate | None:
        return self._candidates.get(candidate_id)
