from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from backend.client_analytics.account_analytics_service import AccountAnalyticsService
from backend.client_analytics.account_models import AccountAnalyticsSummary
from backend.client_analytics.analytics_models import (
    ClientAnalyticsOverview,
    RiskAnalyticsSummary,
    SessionPerformanceSummary,
    SymbolPerformanceSummary,
)
from backend.client_analytics.client_analytics_service import ClientAnalyticsService
from backend.client_analytics.executive_dashboard_service import ExecutiveDashboardService
from backend.client_analytics.executive_models import ExecutiveDashboardSummary, ExecutiveSystemHealth
from backend.client_analytics.export_service import ExportService
from backend.client_analytics.report_builder import ReportBuilder
from backend.client_analytics.report_models import ClientReport
from backend.client_analytics.strategy_analytics_service import StrategyAnalyticsService
from backend.client_analytics.strategy_models import StrategyPerformanceSummary


router = APIRouter(prefix="/client-analytics", tags=["Client Analytics"])
client_analytics_service = ClientAnalyticsService()
account_analytics_service = AccountAnalyticsService()
report_builder = ReportBuilder(client_analytics_service)
export_service = ExportService(report_builder)
strategy_analytics_service = StrategyAnalyticsService()
executive_dashboard_service = ExecutiveDashboardService()


@router.get("/status")
async def get_client_analytics_status() -> dict:
    return client_analytics_service.get_status()


@router.get("/overview", response_model=ClientAnalyticsOverview)
async def get_client_analytics_overview() -> ClientAnalyticsOverview:
    return client_analytics_service.get_overview()


@router.get("/symbols", response_model=list[SymbolPerformanceSummary])
async def get_client_analytics_symbols() -> list[SymbolPerformanceSummary]:
    return client_analytics_service.get_all_symbol_performance()


@router.get("/symbols/{symbol}", response_model=SymbolPerformanceSummary)
async def get_client_analytics_symbol(symbol: str) -> SymbolPerformanceSummary:
    return client_analytics_service.get_symbol_performance(symbol)


@router.get("/sessions", response_model=list[SessionPerformanceSummary])
async def get_client_analytics_sessions() -> list[SessionPerformanceSummary]:
    return client_analytics_service.get_session_performance()


@router.get("/risk", response_model=RiskAnalyticsSummary)
async def get_client_analytics_risk() -> RiskAnalyticsSummary:
    return client_analytics_service.get_risk_analytics()


@router.get("/snapshots/latest", response_model=ClientAnalyticsOverview)
async def get_client_analytics_latest_snapshot() -> ClientAnalyticsOverview:
    return client_analytics_service.get_latest_snapshot()


@router.get("/accounts", response_model=list[AccountAnalyticsSummary])
async def get_client_analytics_accounts() -> list[AccountAnalyticsSummary]:
    return account_analytics_service.get_accounts()


@router.get("/accounts/master", response_model=AccountAnalyticsSummary)
async def get_client_analytics_master_account() -> AccountAnalyticsSummary:
    return account_analytics_service.get_master_account()


@router.get("/accounts/copiers", response_model=list[AccountAnalyticsSummary])
async def get_client_analytics_copier_accounts() -> list[AccountAnalyticsSummary]:
    return account_analytics_service.get_copier_accounts()


@router.get("/accounts/sync-status")
async def get_client_analytics_account_sync_status() -> dict:
    return account_analytics_service.get_sync_status()


@router.get("/accounts/{account_id}", response_model=AccountAnalyticsSummary | None)
async def get_client_analytics_account(account_id: str) -> AccountAnalyticsSummary | None:
    return account_analytics_service.get_account(account_id)


@router.get("/strategy/status")
async def get_client_strategy_status() -> dict:
    return {
        "status": "OPERATIONAL",
        "supported_symbols": ["XAUUSD", "EURUSD", "NIFTY50"],
        "nifty50_status": "SMC_INTELLIGENCE_READY",
        "nifty50_analytics_status": "ANALYTICS_INTEGRATED",
        "simulation_only": True,
        "demo_execution": True,
        "live_execution_enabled": False,
        "broker_execution_enabled": False,
    }


@router.get("/strategy/overview")
async def get_client_strategy_overview() -> dict:
    return strategy_analytics_service.get_strategy_overview()


@router.get("/strategy/performance", response_model=list[StrategyPerformanceSummary])
async def get_client_strategy_performance() -> list[StrategyPerformanceSummary]:
    return strategy_analytics_service.get_all_strategy_performance()


@router.get("/strategy/performance/{symbol}", response_model=StrategyPerformanceSummary)
async def get_client_strategy_symbol_performance(symbol: str) -> StrategyPerformanceSummary:
    return strategy_analytics_service.get_symbol_performance(symbol)


@router.get("/strategy/rankings")
async def get_client_strategy_rankings() -> list[dict]:
    return strategy_analytics_service.get_rankings()


@router.get("/strategy/session-efficiency")
async def get_client_strategy_session_efficiency() -> list[dict]:
    return strategy_analytics_service.get_session_efficiency()


@router.get("/strategy/comparison")
async def get_client_strategy_comparison() -> dict:
    return strategy_analytics_service.get_comparative_analysis()


@router.get("/executive/status")
async def get_executive_dashboard_status() -> dict:
    return executive_dashboard_service.get_status()


@router.get("/executive/summary", response_model=ExecutiveDashboardSummary)
async def get_executive_dashboard_summary() -> ExecutiveDashboardSummary:
    return executive_dashboard_service.get_summary()


@router.get("/executive/readiness")
async def get_executive_readiness_matrix() -> dict:
    return executive_dashboard_service.get_readiness_matrix()


@router.get("/executive/instruments")
async def get_executive_instrument_readiness() -> dict:
    return executive_dashboard_service.get_instrument_readiness()


@router.get("/executive/system-health", response_model=ExecutiveSystemHealth)
async def get_executive_system_health() -> ExecutiveSystemHealth:
    return executive_dashboard_service.get_system_health()


@router.get("/executive/completion")
async def get_executive_completion_report() -> dict:
    return executive_dashboard_service.get_completion_report()


@router.get("/reports/status")
async def get_client_reports_status() -> dict:
    return {
        "status": "OPERATIONAL",
        "supported_reports": ["DAILY", "WEEKLY", "SYMBOL", "RISK", "TRADE_JOURNAL", "EXECUTION_HISTORY"],
        "json_export_ready": True,
        "csv_export_ready": True,
        "simulation_only": True,
        "demo_execution": True,
        "live_execution_enabled": False,
        "broker_execution_enabled": False,
    }


@router.get("/reports/daily", response_model=ClientReport)
async def get_daily_client_report() -> ClientReport:
    return report_builder.build_daily_report()


@router.get("/reports/weekly", response_model=ClientReport)
async def get_weekly_client_report() -> ClientReport:
    return report_builder.build_weekly_report()


@router.get("/reports/symbol/{symbol}", response_model=ClientReport)
async def get_symbol_client_report(symbol: str) -> ClientReport:
    return report_builder.build_symbol_report(symbol)


@router.get("/reports/risk", response_model=ClientReport)
async def get_risk_client_report() -> ClientReport:
    return report_builder.build_risk_report()


@router.get("/reports/trade-journal", response_model=ClientReport)
async def get_trade_journal_client_report() -> ClientReport:
    return report_builder.build_trade_journal_report()


@router.get("/reports/export/json")
async def export_client_report_json() -> dict:
    return export_service.export_json()


@router.get("/reports/export/csv", response_class=PlainTextResponse)
async def export_client_report_csv() -> str:
    return export_service.export_csv()
