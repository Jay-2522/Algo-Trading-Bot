from fastapi import APIRouter, HTTPException

from backend.news_engine.economic_calendar import EconomicCalendarService
from backend.news_engine.news_filter_service import NewsFilterService
from backend.news_intelligence.news_readiness_service import NewsReadinessService
from backend.news_intelligence.news_service import NewsService


router = APIRouter(prefix="/news", tags=["News Intelligence"])
calendar_service = EconomicCalendarService()
news_filter_service = NewsFilterService(calendar=calendar_service)
news_intelligence_service = NewsService()
news_readiness_service = NewsReadinessService()


@router.get("/status")
async def get_news_status() -> dict:
    status = news_intelligence_service.get_status().model_dump(mode="json")
    status.update(
        {
            "legacy_status": "operational",
            "mode": "ARCHITECTURE_ONLY_FOUNDATION",
            "broker_execution_enabled": False,
        }
    )
    return {
        **status,
        "external_feeds_enabled": False,
    }


@router.get("/supported-sources")
async def get_supported_news_sources() -> dict:
    return {
        "sources": news_intelligence_service.get_supported_sources(),
        "external_feeds_enabled": False,
    }


@router.get("/supported-events")
async def get_supported_news_events() -> dict:
    return {
        "event_types": news_intelligence_service.get_supported_events(),
        "currencies": news_intelligence_service.classifier.SUPPORTED_CURRENCIES,
    }


@router.get("/calendar-placeholder")
async def get_calendar_placeholder() -> list[dict]:
    return [event.model_dump(mode="json") for event in news_intelligence_service.build_placeholder_calendar()]


@router.get("/readiness")
async def get_news_readiness() -> dict:
    return news_readiness_service.status()


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
