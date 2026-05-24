from fastapi import APIRouter, HTTPException

from backend.news_engine.economic_calendar import EconomicCalendarService
from backend.news_engine.news_filter_service import NewsFilterService


router = APIRouter(prefix="/news", tags=["News Intelligence"])
calendar_service = EconomicCalendarService()
news_filter_service = NewsFilterService(calendar=calendar_service)


@router.get("/status")
async def get_news_status() -> dict:
    return {
        "status": "operational",
        "external_feeds_enabled": False,
        "mode": "MOCK_CALENDAR_FOUNDATION",
    }


@router.get("/upcoming")
async def get_upcoming_events() -> list[dict]:
    return [event.model_dump(mode="json") for event in calendar_service.get_upcoming_events()]


@router.get("/high-impact")
async def get_high_impact_events() -> list[dict]:
    return [event.model_dump(mode="json") for event in news_filter_service.get_upcoming_high_impact_events()]


@router.get("/risk-status/{symbol}")
async def get_news_risk_status(symbol: str) -> dict:
    try:
        status = news_filter_service.get_news_risk_status(symbol, persist=True)
        return status.model_dump(mode="json")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/allow-trading/{symbol}")
async def allow_trading(symbol: str) -> dict:
    try:
        status = news_filter_service.get_news_risk_status(symbol, persist=True)
        return {
            "trading_allowed": status.trading_allowed,
            "reason": status.reason,
            "risk_level": status.risk_level,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/blackout-windows")
async def get_blackout_windows() -> list[dict]:
    return [window.model_dump(mode="json") for window in news_filter_service.get_blackout_windows()]


@router.get("/macro-score/{symbol}")
async def get_macro_score(symbol: str) -> dict:
    try:
        return news_filter_service.get_macro_score(symbol).model_dump(mode="json")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

