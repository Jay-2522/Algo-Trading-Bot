from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from backend.monitoring.monitoring_service import MonitoringService
from backend.utils.json_safety import safe_error_payload, to_json_safe


router = APIRouter(prefix="/monitoring", tags=["Monitoring & Alerting"])
monitoring_service = MonitoringService()


@router.get("/status")
async def get_monitoring_status() -> JSONResponse:
    try:
        return JSONResponse(content=to_json_safe(monitoring_service.get_status()))
    except Exception as exc:
        return JSONResponse(content=safe_error_payload(f"Monitoring status unavailable: {exc}", "monitoring"))


@router.get("/system-health")
async def get_monitoring_system_health() -> JSONResponse:
    try:
        return JSONResponse(content=to_json_safe(monitoring_service.get_system_health()))
    except Exception as exc:
        return JSONResponse(content=safe_error_payload(f"System health unavailable: {exc}", "monitoring"))


@router.get("/modules")
async def get_monitoring_modules() -> JSONResponse:
    try:
        return JSONResponse(content=to_json_safe(monitoring_service.get_module_health()))
    except Exception:
        return JSONResponse(content=[])


@router.get("/execution")
async def get_monitoring_execution() -> JSONResponse:
    try:
        return JSONResponse(content=to_json_safe(monitoring_service.get_execution_monitoring()))
    except Exception as exc:
        return JSONResponse(content=safe_error_payload(f"Execution monitoring unavailable: {exc}", "monitoring"))


@router.get("/webhooks")
async def get_monitoring_webhooks() -> JSONResponse:
    try:
        return JSONResponse(content=to_json_safe(monitoring_service.get_webhook_monitoring()))
    except Exception as exc:
        return JSONResponse(content=safe_error_payload(f"Webhook monitoring unavailable: {exc}", "monitoring"))


@router.get("/brokers")
async def get_monitoring_brokers() -> JSONResponse:
    try:
        return JSONResponse(content=to_json_safe(monitoring_service.get_broker_monitoring()))
    except Exception as exc:
        return JSONResponse(content=safe_error_payload(f"Broker monitoring unavailable: {exc}", "monitoring"))


@router.get("/alerts")
async def get_monitoring_alerts(limit: int = Query(default=100, ge=1, le=1000)) -> JSONResponse:
    try:
        return JSONResponse(content=to_json_safe(monitoring_service.get_alerts(limit)))
    except Exception:
        return JSONResponse(content=[])


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_monitoring_alert(alert_id: str) -> JSONResponse:
    alert = monitoring_service.acknowledge_alert(alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found.")
    return JSONResponse(content=to_json_safe(alert))
