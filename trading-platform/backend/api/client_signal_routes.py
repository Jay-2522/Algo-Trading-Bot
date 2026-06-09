from fastapi import APIRouter

from backend.strategy.client_signal_center_service import ClientSignalCenterService


router = APIRouter(prefix="/client-signals", tags=["Client Signal Center"])
client_signal_center_service = ClientSignalCenterService()


@router.get("/status")
async def get_client_signal_status() -> dict:
    return client_signal_center_service.status()


@router.get("/current")
async def get_current_client_signals() -> dict:
    return client_signal_center_service.current()


@router.get("/{symbol}")
async def get_client_signal_for_symbol(symbol: str) -> dict:
    return client_signal_center_service.signal_for_symbol(symbol)


@router.post("/refresh")
async def refresh_client_signals() -> dict:
    return client_signal_center_service.refresh()
