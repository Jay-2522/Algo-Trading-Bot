from typing import Any

from backend.dashboard.dashboard_state_provider import DashboardStateProvider, dashboard_state_provider
from backend.execution_dashboard.execution_dashboard_models import (
    ExecutionDashboardCard,
    ExecutionDashboardOverview,
    ExecutionDashboardSummary,
)


class ExecutionDashboardBuilder:
    """Read-only aggregator for Phase 5 execution operations monitoring."""

    def __init__(
        self,
        demo_execution_service: Any,
        multi_account_execution_service: Any,
        trade_copier_service: Any,
        confirmation_service: Any,
        execution_risk_service: Any,
        state_provider: DashboardStateProvider | None = None,
    ) -> None:
        self.demo_execution_service = demo_execution_service
        self.multi_account_execution_service = multi_account_execution_service
        self.trade_copier_service = trade_copier_service
        self.confirmation_service = confirmation_service
        self.execution_risk_service = execution_risk_service
        self.state_provider = state_provider or dashboard_state_provider

    def build_overview(self) -> ExecutionDashboardOverview:
        demo_status = self.demo_execution_service.get_status()
        routing_status = self.multi_account_execution_service.get_status()
        copier_status = self.trade_copier_service.get_status()
        confirmation_status = self.confirmation_service.get_status()
        reconciliation = self.confirmation_service.reconciliation_summary()
        risk_status = self.execution_risk_service.get_status()

        state = self.state_provider.build_state()
        readiness = state.system_status if self._safety_flags_ok() else "REVIEW_REQUIRED"

        return ExecutionDashboardOverview(
            execution_bridge_status=str(demo_status.get("status", "UNKNOWN")),
            routing_status=str(routing_status.get("status", "UNKNOWN")),
            copier_status=str(copier_status.get("status", "UNKNOWN")),
            confirmation_status=str(confirmation_status.get("status", "UNKNOWN")),
            reconciliation_status=self._reconciliation_status(reconciliation),
            risk_status=str(risk_status.get("status", "UNKNOWN")),
            health_score=state.execution_health_score,
            execution_readiness=readiness,
            simulation_only=True,
            live_execution_enabled=False,
            broker_execution_enabled=False,
        )

    def build_cards(self) -> list[ExecutionDashboardCard]:
        overview = self.build_overview()
        summary = self.build_summary()
        return [
            ExecutionDashboardCard(
                title="Execution Bridge",
                value=overview.execution_bridge_status,
                status=self._card_status(overview.execution_bridge_status),
                description=f"{summary.total_demo_executions} guarded demo execution result(s) recorded.",
            ),
            ExecutionDashboardCard(
                title="Multi-Account Routing",
                value=overview.routing_status,
                status=self._card_status(overview.routing_status),
                description=f"{summary.total_multi_account_batches} demo routing batch(es) available for monitoring.",
            ),
            ExecutionDashboardCard(
                title="Trade Copier",
                value=overview.copier_status,
                status=self._card_status(overview.copier_status),
                description=f"{summary.total_copy_batches} copy batch(es) tracked with duplicate protection.",
            ),
            ExecutionDashboardCard(
                title="Confirmations",
                value=str(summary.total_confirmations),
                status=self._card_status(overview.confirmation_status),
                description="Execution confirmation tracker is ingesting demo-only outcomes.",
            ),
            ExecutionDashboardCard(
                title="Reconciliation",
                value=overview.reconciliation_status,
                status=self._card_status(overview.reconciliation_status),
                description=f"{summary.total_reconciliations} reconciliation snapshot(s) summarized.",
            ),
            ExecutionDashboardCard(
                title="Risk Enforcement",
                value=overview.risk_status,
                status=self._card_status(overview.risk_status),
                description=f"{summary.total_risk_decisions} risk decision(s), {summary.blocked_attempts} blocked attempt(s).",
            ),
            ExecutionDashboardCard(
                title="Execution Health Score",
                value=f"{overview.health_score}%",
                status="READY" if overview.health_score >= 80 else "REVIEW",
                description="Composite display health across bridge, routing, copier, confirmation, and risk services.",
            ),
            ExecutionDashboardCard(
                title="Client Readiness",
                value=overview.execution_readiness,
                status="READY" if overview.execution_readiness == "CLIENT_DEMO_READY" else "REVIEW",
                description="Read-only execution operations visibility for client-facing demo readiness.",
            ),
        ]

    def build_summary(self) -> ExecutionDashboardSummary:
        demo_results = self.demo_execution_service.list_results(1000)
        confirmations = self.confirmation_service.list_confirmations(1000)
        reconciliation = self.confirmation_service.reconciliation_summary()
        risk_decisions = self.execution_risk_service.list_decisions(1000)
        copy_batches = self.trade_copier_service.list_batches(1000)
        multi_batches = self.multi_account_execution_service.list_results(1000)
        warnings = self._collect_warnings(demo_results, copy_batches, multi_batches, reconciliation)

        blocked_attempts = sum(1 for result in demo_results if getattr(result, "status", "") in {"BLOCKED", "FAILED_SAFE"})
        blocked_attempts += sum(1 for decision in risk_decisions if getattr(decision, "approved", False) is False)
        blocked_attempts += sum(1 for batch in copy_batches if getattr(batch, "copy_status", "") == "BLOCKED")
        blocked_attempts += sum(1 for batch in multi_batches if getattr(batch, "blocked", 0) or getattr(batch, "rejected", 0))

        return ExecutionDashboardSummary(
            total_demo_executions=len(demo_results),
            total_confirmations=len(confirmations),
            total_reconciliations=1,
            total_risk_decisions=len(risk_decisions),
            total_copy_batches=len(copy_batches),
            total_multi_account_batches=len(multi_batches),
            blocked_attempts=blocked_attempts,
            warnings=warnings,
        )

    def _reconciliation_status(self, reconciliation: Any) -> str:
        if getattr(reconciliation, "mismatched", 0) or getattr(reconciliation, "missing_position", 0):
            return "REVIEW_REQUIRED"
        if getattr(reconciliation, "pending", 0):
            return "PENDING"
        return "CONFIRMED" if getattr(reconciliation, "total_executions", 0) else "NO_EXECUTIONS"

    def _card_status(self, value: str) -> str:
        if value in {"OPERATIONAL", "DEMO_EXECUTION_READY", "CONFIRMED", "NO_EXECUTIONS"}:
            return "READY"
        if value in {"PENDING", "REVIEW_REQUIRED"}:
            return "REVIEW"
        return "BLOCKED"

    def _safety_flags_ok(self) -> bool:
        statuses = [
            self.demo_execution_service.get_status(),
            self.multi_account_execution_service.get_status(),
            self.trade_copier_service.get_status(),
            self.confirmation_service.get_status(),
            self.execution_risk_service.get_status(),
        ]
        return all(
            status.get("simulation_only") is True
            and status.get("live_execution_enabled") is False
            and status.get("broker_execution_enabled") is False
            for status in statuses
        )

    def _collect_warnings(self, demo_results: list[Any], copy_batches: list[Any], multi_batches: list[Any], reconciliation: Any) -> list[str]:
        warnings: list[str] = []
        for source in [*demo_results, *copy_batches, *multi_batches, reconciliation]:
            for warning in getattr(source, "warnings", []) or []:
                if warning not in warnings:
                    warnings.append(str(warning))
        if not warnings:
            warnings.append("Live and broker execution remain disabled; dashboard is read-only.")
        return warnings[:10]
