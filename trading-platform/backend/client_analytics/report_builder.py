from datetime import datetime, timezone
from typing import Any

from backend.client_analytics.client_analytics_service import ClientAnalyticsService
from backend.client_analytics.report_models import ClientReport
from backend.client_analytics.report_store import ReportStore
from backend.nifty50.nifty_reporting_adapter import NIFTYReportingAdapter


class ReportBuilder:
    """Build client reports from existing analytics without fabricating trades or PnL."""

    def __init__(
        self,
        analytics_service: ClientAnalyticsService | None = None,
        store: ReportStore | None = None,
        nifty_reporting: NIFTYReportingAdapter | None = None,
    ) -> None:
        self.analytics_service = analytics_service or ClientAnalyticsService()
        self.store = store or ReportStore()
        self.nifty_reporting = nifty_reporting or NIFTYReportingAdapter()

    def build_daily_report(self) -> ClientReport:
        return self._build_report("DAILY", "TODAY")

    def build_weekly_report(self) -> ClientReport:
        return self._build_report("WEEKLY", "CURRENT_WEEK")

    def build_symbol_report(self, symbol: str) -> ClientReport:
        report = self._build_report("SYMBOL", symbol.upper())
        report.symbol_performance = [self.analytics_service.get_symbol_performance(symbol).model_dump(mode="json")]
        if symbol.upper() == "NIFTY50":
            report.summary["nifty50_reporting"] = self.nifty_reporting.build_symbol_report_section()
        return self.store.store_report(report)

    def build_risk_report(self) -> ClientReport:
        return self._build_report("RISK", "CURRENT")

    def build_trade_journal_report(self) -> ClientReport:
        return self._build_report("TRADE_JOURNAL", "CURRENT")

    def build_execution_history_report(self) -> ClientReport:
        return self._build_report("EXECUTION_HISTORY", "CURRENT")

    def _build_report(self, report_type: str, period: str) -> ClientReport:
        overview = self.analytics_service.get_overview()
        symbols = self.analytics_service.get_all_symbol_performance()
        sessions = self.analytics_service.get_session_performance()
        risk = self.analytics_service.get_risk_analytics()
        data = self.analytics_service.collector.collect_all()
        demo_executions = data.get("demo_executions", [])
        copier_results = data.get("trade_copier_results", [])
        report = ClientReport(
            report_type=report_type,
            period=period,
            generated_at=datetime.now(timezone.utc),
            summary={
                "status": overview.status,
                "total_signals": overview.total_signals,
                "total_demo_executions": overview.total_demo_executions,
                "total_copy_batches": overview.total_copy_batches,
                "win_rate": overview.win_rate,
                "net_pnl": overview.net_pnl,
                "profit_factor": overview.profit_factor,
                "max_drawdown": overview.max_drawdown,
                "empty_report": overview.total_signals == 0 and overview.total_demo_executions == 0,
                "note": "Report contains only recorded demo analytics; no fake trades or PnL are generated.",
                "supported_symbols": overview.supported_symbols,
                "nifty50_status": "ANALYTICS_INTEGRATED",
                "nifty50_strategy_status": "SMC_INTELLIGENCE_READY",
            },
            symbol_performance=[symbol.model_dump(mode="json") for symbol in symbols],
            session_performance=[session.model_dump(mode="json") for session in sessions],
            risk_summary=risk.model_dump(mode="json"),
            trade_journal_summary={
                "entries": len(data.get("strategy_signals", [])),
                "demo_executions": len(demo_executions),
                "pnl_available": any(hasattr(execution, "pnl") for execution in demo_executions),
            },
            execution_summary={
                "demo_executions": len(demo_executions),
                "copy_results": len(copier_results),
                "final_status": "EMPTY" if not demo_executions and not copier_results else "RECORDED",
            },
            simulation_only=True,
            demo_execution=True,
            live_execution_enabled=False,
            broker_execution_enabled=False,
        )
        return self.store.store_report(report)
