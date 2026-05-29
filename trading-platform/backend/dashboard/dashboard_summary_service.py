from backend.phase3_readiness.phase3_readiness_service import Phase3ReadinessService
from backend.dashboard.dashboard_state_provider import DashboardStateProvider, dashboard_state_provider


class DashboardSummaryService:
    """Create concise client-facing dashboard summary text."""

    def __init__(
        self,
        phase3_service: Phase3ReadinessService | None = None,
        state_provider: DashboardStateProvider | None = None,
    ) -> None:
        self.phase3_service = phase3_service or Phase3ReadinessService()
        self.state_provider = state_provider or dashboard_state_provider

    def build_summary(self) -> dict:
        try:
            state = self.state_provider.build_state()
            phase3_status = state.phase3_status
        except Exception:
            phase3_status = "WARNING"
        return {
            "headline": "VPS dashboard backend context is ready for client-facing monitoring.",
            "summary": (
                "The backend can now summarize system health, brokers, TradingView webhooks, "
                "account routing, allocation, execution queue state, simulated lifecycle, alerts, "
                "and Phase 3 readiness in a clean dashboard format."
            ),
            "phase3_status": phase3_status,
            "safety_status": "Simulation-only mode is preserved and live execution remains disabled.",
            "next_step": "Begin Phase 4 dashboard frontend and operator console views.",
            "simulation_only": True,
            "live_execution_enabled": False,
        }
