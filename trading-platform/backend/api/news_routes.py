from typing import Any

from fastapi import APIRouter, Body, HTTPException

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


@router.post("/forex-factory/ingest")
async def ingest_forex_factory_events(payload: list[dict[str, Any]] = Body(default_factory=list)) -> dict:
    events = news_intelligence_service.ingest_forex_factory_events(payload)
    return {
        "ingested": len(events),
        "events": [event.model_dump(mode="json") for event in events],
        "external_api_calls_enabled": False,
        "scraping_enabled": False,
        "simulation_only": True,
    }


@router.get("/calendar")
async def get_news_calendar() -> list[dict]:
    return [event.model_dump(mode="json") for event in news_intelligence_service.list_calendar_events()]


@router.get("/upcoming-events")
async def get_news_upcoming_events() -> list[dict]:
    return [event.model_dump(mode="json") for event in news_intelligence_service.get_upcoming_events()]


@router.get("/risk-context")
async def get_news_risk_context() -> dict:
    return news_intelligence_service.get_news_risk_context().model_dump(mode="json")


@router.get("/filter/status")
async def get_news_filter_status() -> dict:
    return {
        "status": "OPERATIONAL",
        "filter_ready": True,
        "simulation_only": True,
        "live_execution_enabled": False,
        "external_api_calls_enabled": False,
    }


@router.post("/filter/evaluate")
async def evaluate_news_filter(payload: dict[str, Any] | None = Body(default=None)) -> dict:
    payload = payload or {}
    decision = news_intelligence_service.evaluate_filter(
        symbol=payload.get("symbol", "XAUUSD"),
        news_context=payload.get("news_context"),
    )
    return decision.model_dump(mode="json")


@router.get("/filter/current/xauusd")
async def get_current_xauusd_news_filter() -> dict:
    return news_intelligence_service.evaluate_filter(symbol="XAUUSD").model_dump(mode="json")


@router.get("/macro/status")
async def get_macro_status() -> dict:
    return {
        "status": "OPERATIONAL",
        "macro_engine_ready": True,
        "supported_instruments": ["DXY", "US10Y"],
        "simulation_only": True,
        "live_execution_enabled": False,
        "external_api_calls_enabled": False,
    }


@router.post("/macro/context")
async def update_macro_context(payload: dict[str, Any] = Body(default_factory=dict)) -> dict:
    context = news_intelligence_service.update_macro_context(
        symbol=payload.get("symbol", "UNKNOWN"),
        current_value=payload.get("current_value"),
        previous_value=payload.get("previous_value"),
    )
    return context.model_dump(mode="json")


@router.get("/macro/context")
async def get_macro_context() -> list[dict]:
    return [context.model_dump(mode="json") for context in news_intelligence_service.list_macro_contexts()]


@router.get("/macro/xauusd-bias")
async def get_xauusd_macro_bias() -> dict:
    return news_intelligence_service.get_xauusd_macro_bias().model_dump(mode="json")


@router.post("/macro/xauusd-bias/evaluate")
async def evaluate_xauusd_macro_bias(payload: dict[str, Any] | None = Body(default=None)) -> dict:
    payload = payload or {}
    return news_intelligence_service.evaluate_xauusd_macro_bias(
        action=payload.get("action", "WAIT"),
    ).model_dump(mode="json")


@router.post("/headlines/ingest")
async def ingest_headlines(payload: list[dict[str, Any]] = Body(default_factory=list)) -> dict:
    headlines = news_intelligence_service.ingest_headlines(payload)
    return {
        "ingested": len(headlines),
        "headlines": [headline.model_dump(mode="json") for headline in headlines],
        "external_api_calls_enabled": False,
        "scraping_enabled": False,
        "simulation_only": True,
    }


@router.get("/headlines")
async def get_headlines() -> list[dict]:
    return [headline.model_dump(mode="json") for headline in news_intelligence_service.list_headlines()]


@router.get("/headlines/recent")
async def get_recent_headlines(minutes: int = 60) -> list[dict]:
    return [headline.model_dump(mode="json") for headline in news_intelligence_service.recent_headlines(minutes=minutes)]


@router.get("/headlines/risk-context")
async def get_headline_risk_context() -> dict:
    return news_intelligence_service.get_headline_risk_context().model_dump(mode="json")


@router.post("/headlines/evaluate")
async def evaluate_headlines(payload: dict[str, Any] | None = Body(default=None)) -> dict:
    payload = payload or {}
    return news_intelligence_service.evaluate_headlines_for_xauusd(
        action=payload.get("action", "WAIT"),
        headline_context=payload.get("headline_context"),
    ).model_dump(mode="json")


@router.get("/unified-risk/status")
async def get_unified_news_risk_status() -> dict:
    return {
        "status": "OPERATIONAL",
        "orchestrator_ready": True,
        "combines": ["calendar_risk", "news_filter", "dxy_us10y_macro", "headline_risk"],
        "simulation_only": True,
        "live_execution_enabled": False,
        "external_api_calls_enabled": False,
    }


@router.get("/unified-risk/xauusd")
async def get_unified_xauusd_news_risk() -> dict:
    return news_intelligence_service.evaluate_unified_xauusd_risk(action="WAIT").model_dump(mode="json")


@router.post("/unified-risk/evaluate")
async def evaluate_unified_news_risk(payload: dict[str, Any] | None = Body(default=None)) -> dict:
    payload = payload or {}
    return news_intelligence_service.evaluate_unified_xauusd_risk(
        action=payload.get("action", "WAIT"),
        calendar_context=payload.get("calendar_context"),
        news_filter_decision=payload.get("news_filter_decision"),
        macro_context=payload.get("macro_context"),
        headline_context=payload.get("headline_context"),
    ).model_dump(mode="json")


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
