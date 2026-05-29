from typing import Any

from backend.execution_dashboard.execution_dashboard_builder import ExecutionDashboardBuilder
from backend.execution_dashboard.execution_dashboard_models import (
    ExecutionDashboardCard,
    ExecutionDashboardOverview,
    ExecutionDashboardSummary,
)


class ExecutionDashboardService:
    """Service facade for read-only execution dashboard views."""

    def __init__(self, builder: ExecutionDashboardBuilder) -> None:
        self.builder = builder

    def status(self) -> dict[str, Any]:
        overview = self.overview()
        summary = self.summary()
        return {
            "status": "OPERATIONAL",
            "mode": "EXECUTION_OPERATIONS_DASHBOARD_READ_ONLY",
            "dashboard_ready": overview.health_score >= 80,
            "execution_readiness": overview.execution_readiness,
            "health_score": overview.health_score,
            "metric": "Execution Health",
            "metric_source": "DashboardStateProvider",
            "monitored_demo_executions": summary.total_demo_executions,
            "monitored_confirmations": summary.total_confirmations,
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "timestamp": overview.timestamp,
        }

    def overview(self) -> ExecutionDashboardOverview:
        return self.builder.build_overview()

    def cards(self) -> list[ExecutionDashboardCard]:
        return self.builder.build_cards()

    def summary(self) -> ExecutionDashboardSummary:
        return self.builder.build_summary()
