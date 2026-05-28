from backend.demo_mode.demo_mode_models import ClientDemoOverview, ExecutiveKPI
from backend.demo_mode.executive_overview_builder import ExecutiveOverviewBuilder


class ClientDemoService:
    """Service facade for presentation-ready client demo mode outputs."""

    def __init__(self, overview_builder: ExecutiveOverviewBuilder | None = None) -> None:
        self.overview_builder = overview_builder or ExecutiveOverviewBuilder()

    def get_status(self) -> dict:
        return {
            "status": "CLIENT_DEMO_READY",
            "mode": "EXECUTIVE_OVERVIEW_DISPLAY_ONLY",
            "system_online": True,
            "dashboard_ready": True,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "message": "Client demo mode is ready. Live trading remains disabled.",
        }

    def get_overview(self) -> ClientDemoOverview:
        return self.overview_builder.build_overview()

    def get_kpis(self) -> list[ExecutiveKPI]:
        return self.overview_builder.build_kpis()

    def get_pipeline_summary(self) -> dict:
        return {
            "pipeline": self.overview_builder.build_pipeline_summary(),
            "summary": "TradingView alerts are normalized, checked by orchestration and risk layers, routed to accounts, allocated safely, queued, and simulated only.",
            "simulation_only": True,
            "live_execution_enabled": False,
        }
