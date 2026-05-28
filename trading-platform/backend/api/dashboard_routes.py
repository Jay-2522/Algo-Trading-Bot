from fastapi import APIRouter

from backend.dashboard.dashboard_models import DashboardCard, DashboardOverview, DashboardStatusResponse
from backend.dashboard.dashboard_service import DashboardService


router = APIRouter(prefix="/dashboard", tags=["VPS Dashboard"])
dashboard_service = DashboardService()


@router.get("/status", response_model=DashboardStatusResponse)
async def get_dashboard_status() -> DashboardStatusResponse:
    return dashboard_service.get_status()


@router.get("/overview", response_model=DashboardOverview)
async def get_dashboard_overview() -> DashboardOverview:
    return dashboard_service.get_overview()


@router.get("/cards", response_model=list[DashboardCard])
async def get_dashboard_cards() -> list[DashboardCard]:
    return dashboard_service.get_cards()


@router.get("/summary")
async def get_dashboard_summary() -> dict:
    return dashboard_service.get_summary()
