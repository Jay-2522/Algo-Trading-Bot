from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query, Request

from backend.webhooks.tradingview_webhook_service import TradingViewWebhookService
from backend.webhooks.webhook_monitoring_service import WebhookMonitoringService
from backend.webhooks.webhook_models import NormalizedTradingSignal, WebhookEventRecord
from backend.webhooks.webhook_orchestration_models import WebhookOrchestrationDecision
from backend.webhooks.webhook_orchestration_service import WebhookOrchestrationService
from backend.webhooks.webhook_security_models import WebhookSecurityEvent


router = APIRouter(prefix="/webhooks", tags=["TradingView Webhooks"])
tradingview_service = TradingViewWebhookService()
monitoring_service = WebhookMonitoringService(tradingview_service.store)
orchestration_service = WebhookOrchestrationService()


@router.post("/tradingview", response_model=NormalizedTradingSignal)
async def receive_tradingview_webhook(
    request: Request,
    payload: dict[str, Any] = Body(default_factory=dict),
) -> NormalizedTradingSignal:
    try:
        source_ip = request.client.host if request.client else "unknown"
        signal = tradingview_service.process_webhook(payload, source_ip=source_ip)
        if bool(payload.get("orchestrate", False)):
            orchestration_service.process_signal(signal)
        return signal
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
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


@router.get("/orchestration/status")
async def get_webhook_orchestration_status() -> dict:
    return orchestration_service.get_status()


@router.get("/orchestration/decisions", response_model=list[WebhookOrchestrationDecision])
async def get_webhook_orchestration_decisions(
    limit: int = Query(default=50, ge=1, le=500),
) -> list[WebhookOrchestrationDecision]:
    return orchestration_service.get_recent_decisions(limit)


@router.get("/orchestration/decisions/{decision_id}", response_model=WebhookOrchestrationDecision)
async def get_webhook_orchestration_decision(decision_id: str) -> WebhookOrchestrationDecision:
    decision = orchestration_service.get_decision(decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="Webhook orchestration decision not found.")
    return decision


@router.post("/orchestration/test", response_model=WebhookOrchestrationDecision)
async def test_webhook_orchestration(payload: dict[str, Any] = Body(default_factory=dict)) -> WebhookOrchestrationDecision:
    try:
        signal = tradingview_service.normalizer.normalize(payload)
        return orchestration_service.process_signal(signal)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Webhook orchestration test failed safe: {exc}") from exc


@router.get("/security/status")
async def get_webhook_security_status() -> dict:
    return tradingview_service.security_service.get_status()


@router.get("/security/events", response_model=list[WebhookSecurityEvent])
async def get_webhook_security_events(
    limit: int = Query(default=100, ge=1, le=1000),
) -> list[WebhookSecurityEvent]:
    return tradingview_service.security_service.get_security_events(limit)


@router.post("/security/test", response_model=WebhookSecurityEvent)
async def test_webhook_security(payload: dict[str, Any] = Body(default_factory=dict)) -> WebhookSecurityEvent:
    source_ip = str(payload.get("source_ip") or "203.0.113.10")
    test_payload = {key: value for key, value in payload.items() if key != "source_ip"}
    return tradingview_service.security_service.validate_webhook_request(test_payload, source_ip)
