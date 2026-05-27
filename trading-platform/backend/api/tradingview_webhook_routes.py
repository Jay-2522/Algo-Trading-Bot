from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query

from backend.webhooks.tradingview_webhook_service import TradingViewWebhookService
from backend.webhooks.webhook_monitoring_service import WebhookMonitoringService
from backend.webhooks.webhook_models import NormalizedTradingSignal, WebhookEventRecord


router = APIRouter(prefix="/webhooks", tags=["TradingView Webhooks"])
tradingview_service = TradingViewWebhookService()
monitoring_service = WebhookMonitoringService(tradingview_service.store)


@router.post("/tradingview", response_model=NormalizedTradingSignal)
async def receive_tradingview_webhook(payload: dict[str, Any] = Body(default_factory=dict)) -> NormalizedTradingSignal:
    try:
        return tradingview_service.process_webhook(payload)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Webhook failed safe during ingestion.") from exc


@router.get("/status")
async def get_webhook_status() -> dict:
    return tradingview_service.get_status()


@router.get("/events", response_model=list[WebhookEventRecord])
async def get_webhook_events(limit: int = Query(default=50, ge=1, le=500)) -> list[WebhookEventRecord]:
    return monitoring_service.get_recent_events(limit)


@router.get("/events/{event_id}", response_model=WebhookEventRecord)
async def get_webhook_event(event_id: str) -> WebhookEventRecord:
    event = monitoring_service.get_event(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Webhook event not found.")
    return event
