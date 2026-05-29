from collections import deque
from datetime import datetime, timezone
from typing import Any

from backend.execution_risk.execution_risk_models import ExecutionRiskAuditEvent, ExecutionRiskDecision


class ExecutionRiskAuditStore:
    """In-memory store for execution risk decisions and audit events."""

    def __init__(self, max_items: int = 1000) -> None:
        self.decisions: deque[ExecutionRiskDecision] = deque(maxlen=max_items)
        self.events: deque[ExecutionRiskAuditEvent] = deque(maxlen=max_items)

    def store_decision(self, decision: ExecutionRiskDecision) -> ExecutionRiskDecision:
        decision.simulation_only = True
        decision.demo_execution = True
        decision.live_execution_enabled = False
        decision.broker_execution_enabled = False
        self.decisions.appendleft(decision)
        self.store_event(
            ExecutionRiskAuditEvent(
                decision_id=decision.decision_id,
                event_type="EXECUTION_RISK_APPROVED" if decision.approved else "EXECUTION_RISK_BLOCKED",
                message="Execution risk decision recorded.",
                metadata=decision.model_dump(mode="json"),
            )
        )
        return decision

    def list_decisions(self, limit: int = 100) -> list[ExecutionRiskDecision]:
        bounded_limit = max(1, min(int(limit), 1000))
        return list(self.decisions)[:bounded_limit]

    def store_event(self, event: ExecutionRiskAuditEvent | str, message: str | None = None, metadata: dict[str, Any] | None = None) -> ExecutionRiskAuditEvent:
        if isinstance(event, ExecutionRiskAuditEvent):
            audit_event = event
        else:
            audit_event = ExecutionRiskAuditEvent(
                event_type=event,
                message=message or "Execution risk audit event.",
                metadata=metadata or {},
                timestamp=datetime.now(timezone.utc),
            )
        audit_event.simulation_only = True
        audit_event.demo_execution = True
        audit_event.live_execution_enabled = False
        audit_event.broker_execution_enabled = False
        self.events.appendleft(audit_event)
        return audit_event

    def list_events(self, limit: int = 100) -> list[ExecutionRiskAuditEvent]:
        bounded_limit = max(1, min(int(limit), 1000))
        return list(self.events)[:bounded_limit]
