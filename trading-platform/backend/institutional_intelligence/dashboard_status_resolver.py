from backend.institutional_intelligence.dashboard_context_models import DashboardCard, DashboardStatus
from backend.institutional_intelligence.institutional_orchestration_models import InstitutionalOrchestrationReport


class DashboardStatusResolver:
    """Resolve a dashboard state without increasing trading permissions."""

    def resolve_dashboard_status(
        self,
        cards: list[DashboardCard],
        orchestration_report: InstitutionalOrchestrationReport | None = None,
    ) -> DashboardStatus:
        if orchestration_report and (
            orchestration_report.live_execution_enabled or not orchestration_report.simulation_only
        ):
            return "CRITICAL"
        final_state = (
            orchestration_report.system_state.final_state
            if orchestration_report and orchestration_report.system_state
            else None
        )
        if final_state == "ERROR_SAFE_MODE":
            return "CRITICAL"
        if final_state == "BLOCKED":
            return "BLOCKED"
        if final_state == "WAITING_FOR_CONFIRMATION":
            return "WAITING"
        if final_state == "MANAGING_POSITION":
            return "ACTIVE"
        warning_count = sum(card.status in {"WARNING", "CRITICAL"} for card in cards)
        if warning_count >= 2:
            return "WARNING"
        if orchestration_report and orchestration_report.simulation_only:
            return "HEALTHY"
        return "INACTIVE"
