from backend.dashboard.dashboard_card_service import DashboardCardService
from backend.dashboard.dashboard_models import DashboardCard, DashboardOverview, DashboardStatusResponse
from backend.dashboard.dashboard_status_builder import DashboardStatusBuilder
from backend.dashboard.dashboard_summary_service import DashboardSummaryService


class DashboardService:
    """Facade for VPS dashboard backend context."""

    def __init__(
        self,
        status_builder: DashboardStatusBuilder | None = None,
        card_service: DashboardCardService | None = None,
        summary_service: DashboardSummaryService | None = None,
    ) -> None:
        self.status_builder = status_builder or DashboardStatusBuilder()
        self.card_service = card_service or DashboardCardService()
        self.summary_service = summary_service or DashboardSummaryService()

    def get_status(self) -> DashboardStatusResponse:
        return self.status_builder.build_status()

    def get_overview(self) -> DashboardOverview:
        return self.status_builder.build_overview()

    def get_cards(self) -> list[DashboardCard]:
        return self.card_service.build_cards()

    def get_summary(self) -> dict:
        return self.summary_service.build_summary()
