from backend.portfolio.account_analytics_service import AccountAnalyticsService
from backend.portfolio.exposure_summary_service import ExposureSummaryService
from backend.portfolio.portfolio_models import PortfolioAccountSummary, PortfolioExposureSummary, PortfolioOverview
from backend.portfolio.portfolio_summary_builder import PortfolioSummaryBuilder


class PortfolioService:
    """Simulation-only portfolio analytics facade for dashboard display."""

    def __init__(
        self,
        account_analytics_service: AccountAnalyticsService | None = None,
        exposure_summary_service: ExposureSummaryService | None = None,
        summary_builder: PortfolioSummaryBuilder | None = None,
    ) -> None:
        self.account_analytics_service = account_analytics_service or AccountAnalyticsService()
        self.exposure_summary_service = exposure_summary_service or ExposureSummaryService()
        self.summary_builder = summary_builder or PortfolioSummaryBuilder(
            self.account_analytics_service,
            self.exposure_summary_service,
        )

    def get_status(self) -> dict:
        accounts = self.get_accounts()
        exposure = self.get_exposure()
        return {
            "status": "SIMULATION_PORTFOLIO_READY",
            "mode": "PORTFOLIO_DISPLAY_ONLY",
            "accounts": len(accounts),
            "enabled_accounts": exposure.enabled_accounts,
            "total_simulated_balance": exposure.total_simulated_balance,
            "total_simulated_equity": exposure.total_simulated_equity,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def get_overview(self) -> PortfolioOverview:
        return self.summary_builder.build_overview()

    def get_accounts(self) -> list[PortfolioAccountSummary]:
        return self.account_analytics_service.get_accounts()

    def get_exposure(self) -> PortfolioExposureSummary:
        return self.exposure_summary_service.build_exposure(self.get_accounts())

    def get_pnl_summary(self) -> dict:
        return self.summary_builder.build_pnl_summary()
