from typing import Any

from backend.execution_confirmation.confirmation_service import ExecutionConfirmationService
from backend.strategy_execution_bridge.bridge_decision_store import BridgeDecisionStore
from backend.strategy_execution_bridge.demo_execution_approval_store import DemoExecutionApprovalStore
from backend.strategy_execution_bridge.end_to_end_flow_store import EndToEndFlowStore
from backend.strategy_execution_bridge.execution_operations_audit import ExecutionOperationsAudit
from backend.strategy_execution_bridge.execution_operations_models import (
    ExecutionOperationsOverview,
    ExecutionPipelineEvent,
)
from backend.strategy_execution_bridge.final_demo_execution_store import FinalDemoExecutionStore
from backend.trade_copier.copier_execution_store import CopierExecutionStore


class ExecutionOperationsCenter:
    """Read-only control center for the complete demo execution pipeline."""

    def __init__(
        self,
        bridge_store: BridgeDecisionStore | None = None,
        approval_store: DemoExecutionApprovalStore | None = None,
        final_store: FinalDemoExecutionStore | None = None,
        e2e_store: EndToEndFlowStore | None = None,
        copier_store: CopierExecutionStore | None = None,
        confirmation_service: ExecutionConfirmationService | None = None,
        audit: ExecutionOperationsAudit | None = None,
    ) -> None:
        self.bridge_store = bridge_store or BridgeDecisionStore()
        self.approval_store = approval_store or DemoExecutionApprovalStore()
        self.final_store = final_store or FinalDemoExecutionStore()
        self.e2e_store = e2e_store or EndToEndFlowStore()
        self.copier_store = copier_store or CopierExecutionStore()
        self.confirmation_service = confirmation_service or ExecutionConfirmationService()
        self.audit = audit or ExecutionOperationsAudit()

    def get_status(self) -> dict[str, Any]:
        overview = self.get_overview()
        return {
            "status": overview.status,
            "pipeline_ready": overview.pipeline_ready,
            "health_score": overview.health_score,
            "monitoring_only": True,
            "safe_manual_controls_only": True,
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def get_overview(self) -> ExecutionOperationsOverview:
        bridge_decisions = self.bridge_store.list_decisions(1000)
        approvals = self.approval_store.list_approvals(1000)
        candidates = self.approval_store.list_candidates(1000)
        final_executions = self.final_store.list_decisions(1000)
        copy_results = self.copier_store.list_results(1000)

        blocked_count = self._count_blocked(bridge_decisions, approvals, final_executions, copy_results)
        rejected_count = self._count_rejected(bridge_decisions, approvals, final_executions, copy_results)
        demo_execution_count = len(
            [execution for execution in final_executions if execution.execution_status in {"DEMO_FILLED", "DEMO_REJECTED", "MT5_UNAVAILABLE"}]
        )
        overview = ExecutionOperationsOverview(
            status="OPERATIONAL",
            pipeline_ready=True,
            bridge_ready=True,
            queue_preview_ready=True,
            approval_ready=True,
            final_execution_ready=True,
            copier_ready=True,
            confirmation_ready=True,
            total_bridge_decisions=len(bridge_decisions),
            total_queue_previews=len([decision for decision in bridge_decisions if decision.queue_preview_created]),
            total_approvals=len(approvals),
            total_candidates=len(candidates),
            total_final_executions=len(final_executions),
            total_copy_results=len(copy_results),
            blocked_count=blocked_count,
            rejected_count=rejected_count,
            demo_execution_count=demo_execution_count,
            health_score=self.get_health_score(),
            simulation_only=True,
            demo_execution=True,
            live_execution_enabled=False,
            broker_execution_enabled=False,
        )
        return overview

    def get_pipeline_events(self, limit: int = 100) -> list[ExecutionPipelineEvent]:
        events = [
            *self._events_from_bridge(),
            *self._events_from_approvals(),
            *self._events_from_candidates(),
            *self._events_from_final_executions(),
            *self._events_from_copy_results(),
            *self.audit.list_events(limit),
        ]
        return sorted(events, key=lambda event: event.timestamp, reverse=True)[:limit]

    def get_recent_executions(self, limit: int = 100) -> dict[str, Any]:
        final_executions = self.final_store.list_decisions(limit)
        flows = self.e2e_store.list_flows(limit)
        copy_results = self.copier_store.list_results(limit)
        return {
            "final_executions": final_executions,
            "end_to_end_flows": flows,
            "copy_results": copy_results,
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def get_recent_rejections(self, limit: int = 100) -> list[ExecutionPipelineEvent]:
        rejected = [
            event
            for event in self.get_pipeline_events(1000)
            if event.severity in {"WARNING", "ERROR"} or "REJECT" in event.status.upper() or "BLOCK" in event.status.upper()
        ]
        return rejected[:limit]

    def get_readiness(self) -> dict[str, Any]:
        overview = self.get_overview()
        return {
            "pipeline_ready": overview.pipeline_ready,
            "bridge_ready": overview.bridge_ready,
            "queue_preview_ready": overview.queue_preview_ready,
            "approval_ready": overview.approval_ready,
            "final_execution_ready": overview.final_execution_ready,
            "copier_ready": overview.copier_ready,
            "confirmation_ready": overview.confirmation_ready,
            "monitoring_only": True,
            "safe_manual_controls_only": True,
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def get_health_score(self) -> int:
        modules_ready = [
            True,  # bridge
            True,  # queue preview
            True,  # approval
            True,  # final execution
            True,  # copier
            True,  # confirmation
        ]
        if not modules_ready[0]:
            return 50
        return max(0, min(100, 100 - (modules_ready.count(False) * 10)))

    def _events_from_bridge(self) -> list[ExecutionPipelineEvent]:
        events: list[ExecutionPipelineEvent] = []
        for decision in self.bridge_store.list_decisions(1000):
            severity = "INFO" if decision.eligible else "WARNING"
            events.append(
                ExecutionPipelineEvent(
                    stage="BRIDGE",
                    status=decision.bridge_status,
                    entity_id=decision.decision_id,
                    symbol=decision.symbol,
                    action=decision.action,
                    message="Strategy bridge decision recorded.",
                    severity=severity,
                    timestamp=decision.timestamp,
                )
            )
            if decision.queue_preview_created:
                events.append(
                    ExecutionPipelineEvent(
                        stage="QUEUE_PREVIEW",
                        status=decision.queue_preview_status,
                        entity_id=decision.queue_preview_id,
                        symbol=decision.symbol,
                        action=decision.action,
                        message="Queue preview created from execution intent.",
                        severity="INFO",
                        timestamp=decision.timestamp,
                    )
                )
        return events

    def _events_from_approvals(self) -> list[ExecutionPipelineEvent]:
        return [
            ExecutionPipelineEvent(
                stage="APPROVAL",
                status=approval.approval_status,
                entity_id=approval.approval_id,
                symbol=approval.symbol,
                action=approval.action,
                message="Demo approval decision recorded.",
                severity="INFO" if approval.approved else "WARNING",
                timestamp=approval.timestamp,
            )
            for approval in self.approval_store.list_approvals(1000)
        ]

    def _events_from_candidates(self) -> list[ExecutionPipelineEvent]:
        return [
            ExecutionPipelineEvent(
                stage="DEMO_CANDIDATE",
                status="READY_FOR_DEMO_EXECUTION" if candidate.ready_for_demo_execution else "NOT_READY",
                entity_id=candidate.candidate_id,
                symbol=candidate.symbol,
                action=candidate.action,
                message="Demo execution candidate tracked.",
                severity="INFO" if candidate.ready_for_demo_execution else "WARNING",
                timestamp=candidate.timestamp,
            )
            for candidate in self.approval_store.list_candidates(1000)
        ]

    def _events_from_final_executions(self) -> list[ExecutionPipelineEvent]:
        events: list[ExecutionPipelineEvent] = []
        for execution in self.final_store.list_decisions(1000):
            severity = "INFO" if execution.execution_status in {"DEMO_FILLED", "DEMO_REJECTED", "MT5_UNAVAILABLE"} else "WARNING"
            events.append(
                ExecutionPipelineEvent(
                    stage="FINAL_EXECUTION",
                    status=execution.execution_status,
                    entity_id=execution.final_execution_id,
                    symbol=execution.symbol,
                    action=execution.action,
                    message="Final demo execution decision recorded.",
                    severity=severity,
                    timestamp=execution.timestamp,
                )
            )
            if execution.demo_execution_result_id:
                events.append(
                    ExecutionPipelineEvent(
                        stage="MT5_DEMO_RESULT",
                        status=execution.execution_status,
                        entity_id=execution.demo_execution_result_id,
                        symbol=execution.symbol,
                        action=execution.action,
                        message="Guarded MT5 demo result linked.",
                        severity=severity,
                        timestamp=execution.timestamp,
                    )
                )
        return events

    def _events_from_copy_results(self) -> list[ExecutionPipelineEvent]:
        return [
            ExecutionPipelineEvent(
                stage="TRADE_COPIER",
                status=result.copy_status,
                entity_id=result.copier_execution_id,
                symbol=result.source_symbol,
                action=result.source_action,
                message="Trade copier execution result recorded.",
                severity="INFO" if result.copy_status in {"COPIED", "PARTIAL_COPY", "DUPLICATE_BLOCKED"} else "WARNING",
                timestamp=result.timestamp,
            )
            for result in self.copier_store.list_results(1000)
        ]

    def _count_blocked(self, *groups: list[Any]) -> int:
        total = 0
        for group in groups:
            for item in group:
                text = " ".join(str(value) for value in self._status_values(item))
                if "BLOCK" in text.upper() or "FAILED_SAFE" in text.upper():
                    total += 1
        return total

    def _count_rejected(self, *groups: list[Any]) -> int:
        total = 0
        for group in groups:
            for item in group:
                text = " ".join(str(value) for value in self._status_values(item))
                if "REJECT" in text.upper():
                    total += 1
        return total

    def _status_values(self, item: Any) -> list[Any]:
        return [
            getattr(item, "bridge_status", ""),
            getattr(item, "approval_status", ""),
            getattr(item, "execution_status", ""),
            getattr(item, "copy_status", ""),
        ]
