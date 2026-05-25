from fastapi import APIRouter, HTTPException

from backend.trading_loop.loop_models import LoopConfig, LoopControlResponse, LoopRunResult, LoopStatus
from backend.trading_loop.loop_service import TradingLoopService


router = APIRouter(prefix="/trading-loop", tags=["Background Trading Loop"])
trading_loop_service = TradingLoopService()


@router.get("/status", response_model=LoopStatus)
async def get_loop_status() -> LoopStatus:
    return trading_loop_service.get_status()


@router.get("/config", response_model=LoopConfig)
async def get_loop_config() -> LoopConfig:
    return trading_loop_service.get_config()


@router.post("/start", response_model=LoopControlResponse)
async def start_loop() -> LoopControlResponse:
    return await trading_loop_service.start_loop()


@router.post("/stop", response_model=LoopControlResponse)
async def stop_loop() -> LoopControlResponse:
    return await trading_loop_service.stop_loop()


@router.post("/pause", response_model=LoopControlResponse)
async def pause_loop() -> LoopControlResponse:
    return await trading_loop_service.pause_loop()


@router.post("/resume", response_model=LoopControlResponse)
async def resume_loop() -> LoopControlResponse:
    return await trading_loop_service.resume_loop()


@router.post("/run-once", response_model=list[LoopRunResult])
async def run_once() -> list[LoopRunResult]:
    return await trading_loop_service.run_once()


@router.get("/symbols")
async def get_symbols() -> dict:
    return {"symbols": trading_loop_service.get_config().monitored_symbols}


@router.post("/symbols/{symbol}")
async def add_symbol(symbol: str) -> dict:
    try:
        return {"symbols": trading_loop_service.add_symbol(symbol)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/symbols/{symbol}")
async def remove_symbol(symbol: str) -> dict:
    try:
        return {"symbols": trading_loop_service.remove_symbol(symbol)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
