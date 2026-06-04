from backend.client_analytics.analytics_models import RiskAnalyticsSummary, SymbolPerformanceSummary


class NIFTYAnalyticsService:
    """Read-only NIFTY50 analytics adapter with no fabricated metrics."""

    def get_status(self) -> dict:
        return {
            "status": "ANALYTICS_INTEGRATED",
            "symbol": "NIFTY50",
            "metrics_source": "RECORDED_NIFTY50_EVENTS_ONLY",
            "fake_metrics_enabled": False,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def get_symbol_summary(self) -> SymbolPerformanceSummary:
        return SymbolPerformanceSummary(symbol="NIFTY50")

    def get_risk_summary(self) -> RiskAnalyticsSummary:
        return RiskAnalyticsSummary()

    def get_strategy_status(self) -> dict:
        return {
            "symbol": "NIFTY50",
            "status": "SMC_INTELLIGENCE_READY",
            "analytics_integrated": True,
            "execution_ready": False,
            "broker_execution_enabled": False,
        }
