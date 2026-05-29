from backend.operational_intelligence.operational_models import (
    OperationalHealthSummary,
    OperationalModuleStatus,
    WarningSummary,
)


class MonitoringSummaryBuilder:
    """Build top-level operational health summaries."""

    def build_summary(
        self,
        statuses: list[OperationalModuleStatus],
        warnings: list[WarningSummary],
        active_alerts: int,
        health_score: int,
        overall_status: str,
    ) -> OperationalHealthSummary:
        return OperationalHealthSummary(
            overall_status=overall_status,
            health_score=health_score,
            active_warnings=len([warning for warning in warnings if warning.severity in {"WARNING", "ERROR", "CRITICAL"}]),
            active_alerts=active_alerts,
            monitored_modules=len(statuses),
            simulation_only=True,
            live_execution_enabled=False,
        )
