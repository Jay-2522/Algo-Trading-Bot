from typing import Any

from fastapi import APIRouter, Body, Query
from fastapi.responses import JSONResponse

from backend.api.execution_queue_routes import execution_queue_service
from backend.api.monitoring_routes import monitoring_service
from backend.control_center.control_center_service import ControlCenterService
from backend.utils.json_safety import safe_error_payload, to_json_safe


router = APIRouter(prefix="/control-center", tags=["Control Center"])
control_center_service = ControlCenterService(
    execution_queue_service=execution_queue_service,
    monitoring_service=monitoring_service,
)


def _reason(payload: dict[str, Any] | None, fallback: str) -> str:
    if not payload:
        return fallback
    return str(payload.get("reason") or fallback)


@router.get("/status")
async def get_control_center_status() -> JSONResponse:
    try:
        return JSONResponse(content=to_json_safe(control_center_service.get_status()))
    except Exception as exc:
        return JSONResponse(content=safe_error_payload(f"Control center status unavailable: {exc}", "control_center"))


@router.get("/safety-state")
async def get_control_center_safety_state() -> JSONResponse:
    try:
        return JSONResponse(content=to_json_safe(control_center_service.get_safety_state()))
    except Exception as exc:
        return JSONResponse(content=safe_error_payload(f"Safety state unavailable: {exc}", "control_center"))


@router.get("/audit-events")
async def get_control_center_audit_events(limit: int = Query(default=100, ge=1, le=1000)) -> JSONResponse:
    try:
        return JSONResponse(content=to_json_safe(control_center_service.get_audit_events(limit)))
    except Exception:
        return JSONResponse(content=[])


@router.post("/queue/pause")
async def pause_simulation_queue(payload: dict[str, Any] = Body(default_factory=dict)) -> JSONResponse:
    action = control_center_service.pause_queue(_reason(payload, "Paused by dashboard operator."))
    return JSONResponse(content=to_json_safe(action))


@router.post("/queue/resume")
async def resume_simulation_queue(payload: dict[str, Any] = Body(default_factory=dict)) -> JSONResponse:
    action = control_center_service.resume_queue(_reason(payload, "Resumed by dashboard operator."))
    return JSONResponse(content=to_json_safe(action))


@router.post("/queue/{queue_id}/cancel")
async def cancel_simulation_queue_item(
    queue_id: str,
    payload: dict[str, Any] = Body(default_factory=dict),
) -> JSONResponse:
    action = control_center_service.cancel_queue_item(queue_id, _reason(payload, "Cancelled by dashboard operator."))
    return JSONResponse(content=to_json_safe(action))


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_control_center_alert(
    alert_id: str,
    payload: dict[str, Any] = Body(default_factory=dict),
) -> JSONResponse:
    action = control_center_service.acknowledge_alert(alert_id, _reason(payload, "Acknowledged by dashboard operator."))
    return JSONResponse(content=to_json_safe(action))


@router.post("/emergency-stop-placeholder")
async def activate_emergency_stop_placeholder(payload: dict[str, Any] = Body(default_factory=dict)) -> JSONResponse:
    action = control_center_service.emergency_stop_placeholder(
        _reason(payload, "Emergency stop placeholder activated by dashboard operator.")
    )
    return JSONResponse(content=to_json_safe(action))
