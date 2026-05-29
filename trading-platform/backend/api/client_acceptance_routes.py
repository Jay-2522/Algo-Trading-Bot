from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.client_acceptance.delivery_readiness_service import DeliveryReadinessService
from backend.utils.json_safety import safe_error_payload, to_json_safe


router = APIRouter(prefix="/client-acceptance", tags=["Client Acceptance"])
client_acceptance_service = DeliveryReadinessService()


@router.get("/status")
async def get_client_acceptance_status() -> JSONResponse:
    try:
        return JSONResponse(content=to_json_safe(client_acceptance_service.get_status()))
    except Exception as exc:
        return JSONResponse(content=safe_error_payload(f"Client acceptance status unavailable: {exc}", "client_acceptance"))


@router.get("/readiness")
async def get_client_acceptance_readiness() -> JSONResponse:
    try:
        return JSONResponse(content=to_json_safe(client_acceptance_service.get_readiness()))
    except Exception as exc:
        return JSONResponse(content=safe_error_payload(f"Client readiness unavailable: {exc}", "client_acceptance"))


@router.get("/checklist")
async def get_client_acceptance_checklist() -> JSONResponse:
    try:
        return JSONResponse(content=to_json_safe(client_acceptance_service.get_checklist()))
    except Exception:
        return JSONResponse(content=[])


@router.get("/remaining-items")
async def get_client_acceptance_remaining_items() -> JSONResponse:
    try:
        return JSONResponse(content=to_json_safe(client_acceptance_service.get_remaining_items()))
    except Exception as exc:
        return JSONResponse(content=safe_error_payload(f"Remaining delivery items unavailable: {exc}", "client_acceptance"))
