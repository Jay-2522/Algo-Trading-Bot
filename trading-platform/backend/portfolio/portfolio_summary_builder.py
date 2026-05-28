from backend.portfolio.account_analytics_service import AccountAnalyticsService
from backend.portfolio.exposure_summary_service import ExposureSummaryService
from backend.portfolio.portfolio_models import PortfolioOverview


class PortfolioSummaryBuilder:
    """Compose account, exposure, and placeholder P&L into one dashboard overview."""

    def __init__(
        self,
        account_analytics_service: AccountAnalyticsService | None = None,
        exposure_summary_service: ExposureSummaryService | None = None,
    ) -> None:
        self.account_analytics_service = account_analytics_service or AccountAnalyticsService()
        self.exposure_summary_service = exposure_summary_service or ExposureSummaryService()

    def build_pnl_summary(self) -> dict:
        return {
            "realized_pnl": 0.0,
            "floating_pnl": 0.0,
            "net_pnl": 0.0,
            "status": "SIMULATED_PLACEHOLDER",
            "message": "No live broker P&L is tracked. Simulated P&L will populate from future demo lifecycle analytics.",
            "simulation_only": True,
            "live_execution_enabled": False,
        }

    def build_overview(self) -> PortfolioOverview:
        accounts = self.account_analytics_service.get_accounts()
        exposure = self.exposure_summary_service.build_exposure(accounts)
        warnings = []
        if "NIFTY50" in exposure.blocked_symbols:
            warnings.append("NIFTY50 remains conditional and blocked until Indian broker integration is complete.")
        return PortfolioOverview(
            portfolio_status="SIMULATION_READY",
            accounts=accounts,
            exposure_summary=exposure,
            pnl_summary=self.build_pnl_summary(),
            warnings=warnings,
            simulation_only=True,
            live_execution_enabled=False,
        )
