from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from backend.monitoring.monitoring_service import MonitoringService
from backend.monitoring.api_monitor import APIMonitor
from backend.monitoring.log_store import LogStore
from backend.monitoring.mt5_monitor import MT5Monitor
from backend.monitoring.platform_health_service import PlatformHealthService
from backend.monitoring.process_monitor import ProcessMonitor
from backend.monitoring.system_metrics import SystemMetrics
from backend.utils.json_safety import safe_error_payload, to_json_safe


router = APIRouter(prefix="/monitoring", tags=["Monitoring & Alerting"])
monitoring_service = MonitoringService()
platform_health_service = PlatformHealthService()
system_metrics = SystemMetrics()
process_monitor = ProcessMonitor()
api_monitor = APIMonitor()
mt5_monitor = MT5Monitor()
log_store = LogStore()


@router.get("/status")
async def get_monitoring_status() -> JSONResponse:
    try:
        payload = monitoring_service.get_status()
        payload.update(
            {
                "status": "OPERATIONAL",
                "production_monitoring_ready": True,
                "structured_logging_ready": True,
                "log_rotation_ready": True,
                "simulation_only": True,
                "demo_execution": True,
                "live_execution_enabled": False,
                "broker_execution_enabled": False,
            }
        )
        return JSONResponse(content=to_json_safe(payload))
    except Exception as exc:
        return JSONResponse(content=safe_error_payload(f"Monitoring status unavailable: {exc}", "monitoring"))


@router.get("/health")
async def get_platform_monitoring_health() -> JSONResponse:
    return JSONResponse(content=to_json_safe(platform_health_service.get_overview()))


@router.get("/metrics")
async def get_platform_system_metrics() -> JSONResponse:
    payload = system_metrics.get_metrics()
    payload.update(
        {
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }
    )
    return JSONResponse(content=to_json_safe(payload))


@router.get("/processes")
async def get_platform_processes() -> JSONResponse:
    return JSONResponse(content=to_json_safe(process_monitor.get_process_status()))


@router.get("/apis")
async def get_platform_api_health() -> JSONResponse:
    return JSONResponse(content=to_json_safe(api_monitor.get_api_health()))


@router.get("/mt5")
async def get_platform_mt5_monitoring() -> JSONResponse:
    return JSONResponse(content=to_json_safe(mt5_monitor.get_mt5_status()))


@router.get("/logs")
async def get_platform_recent_logs(limit: int = Query(default=100, ge=1, le=1000)) -> JSONResponse:
    return JSONResponse(content=to_json_safe(log_store.get_recent_logs(limit)))


@router.get("/logs/errors")
async def get_platform_error_logs(limit: int = Query(default=100, ge=1, le=1000)) -> JSONResponse:
    return JSONResponse(content=to_json_safe(log_store.get_error_logs(limit)))


@router.get("/logs/warnings")
async def get_platform_warning_logs(limit: int = Query(default=100, ge=1, le=1000)) -> JSONResponse:
    return JSONResponse(content=to_json_safe(log_store.get_warning_logs(limit)))


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
