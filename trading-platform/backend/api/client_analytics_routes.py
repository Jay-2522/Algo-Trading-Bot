from fastapi import APIRouter

from backend.client_analytics.analytics_models import (
    ClientAnalyticsOverview,
    RiskAnalyticsSummary,
    SessionPerformanceSummary,
    SymbolPerformanceSummary,
)
from backend.client_analytics.client_analytics_service import ClientAnalyticsService


router = APIRouter(prefix="/client-analytics", tags=["Client Analytics"])
client_analytics_service = ClientAnalyticsService()


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
