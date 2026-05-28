from fastapi import APIRouter, HTTPException, Query

from backend.monitoring.monitoring_models import AlertEvent, ExecutionMonitoringSummary, ModuleHealthStatus, SystemHealthSnapshot
from backend.monitoring.monitoring_service import MonitoringService


router = APIRouter(prefix="/monitoring", tags=["Monitoring & Alerting"])
monitoring_service = MonitoringService()


@router.get("/status")
async def get_monitoring_status() -> dict:
    return monitoring_service.get_status()


@router.get("/system-health", response_model=SystemHealthSnapshot)
async def get_monitoring_system_health() -> SystemHealthSnapshot:
    return monitoring_service.get_system_health()


@router.get("/modules", response_model=list[ModuleHealthStatus])
async def get_monitoring_modules() -> list[ModuleHealthStatus]:
    return monitoring_service.get_module_health()


@router.get("/execution", response_model=ExecutionMonitoringSummary)
async def get_monitoring_execution() -> ExecutionMonitoringSummary:
    return monitoring_service.get_execution_monitoring()


@router.get("/webhooks")
async def get_monitoring_webhooks() -> dict:
    return monitoring_service.get_webhook_monitoring()


@router.get("/brokers")
async def get_monitoring_brokers() -> dict:
    return monitoring_service.get_broker_monitoring()


@router.get("/alerts", response_model=list[AlertEvent])
async def get_monitoring_alerts(limit: int = Query(default=100, ge=1, le=1000)) -> list[AlertEvent]:
    return monitoring_service.get_alerts(limit)


@router.post("/alerts/{alert_id}/acknowledge", response_model=AlertEvent)
async def acknowledge_monitoring_alert(alert_id: str) -> AlertEvent:
    alert = monitoring_service.acknowledge_alert(alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found.")
    return alert
