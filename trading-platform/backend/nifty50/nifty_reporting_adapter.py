from backend.nifty50.nifty_analytics_service import NIFTYAnalyticsService


class NIFTYReportingAdapter:
    """Build honest NIFTY50 report sections from available analytics only."""

    def __init__(self, analytics_service: NIFTYAnalyticsService | None = None) -> None:
        self.analytics_service = analytics_service or NIFTYAnalyticsService()

    def build_symbol_report_section(self) -> dict:
        summary = self.analytics_service.get_symbol_summary()
        return {
            "symbol": "NIFTY50",
            "status": "ANALYTICS_INTEGRATED",
            "strategy_status": "SMC_INTELLIGENCE_READY",
            "execution_ready": False,
            "broker_execution_enabled": False,
            "note": "NIFTY50 analytics are integrated; metrics remain zero until recorded NIFTY50 activity exists.",
            "symbol_performance": summary.model_dump(mode="json"),
        }
