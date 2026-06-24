import asyncio

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from backend.streaming.market_stream_service import MarketStreamService
from backend.streaming.stream_models import StreamControlResponse, StreamStatus, TickMessage
from backend.utils.logger import get_logger


router = APIRouter(prefix="/streaming", tags=["Live Streaming"])
websocket_router = APIRouter(tags=["Live Streaming"])
market_stream_service = MarketStreamService()
TICK_READ_TIMEOUT_SECONDS = 0.8
logger = get_logger(__name__)


async def _get_tick_with_timeout(symbol: str) -> TickMessage:
    normalized_symbol = symbol.strip().upper() if symbol else ""
    if not normalized_symbol:
        raise ValueError("Symbol cannot be empty.")
    try:
        return market_stream_service.get_tick_once(normalized_symbol)
    except Exception as exc:
        logger.warning("PRICE_FEED_FALLBACK_USED %s reason=%s", normalized_symbol, exc)
        return market_stream_service.tick_streamer.get_simulated_tick(normalized_symbol)


@router.get("/status", response_model=StreamStatus)
async def get_streaming_status() -> StreamStatus:
    return market_stream_service.get_status()


@router.post("/start/{symbol}", response_model=StreamControlResponse)
async def start_stream(symbol: str) -> StreamControlResponse:
    try:
        return market_stream_service.start_stream(symbol)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/stop/{symbol}", response_model=StreamControlResponse)
async def stop_stream(symbol: str) -> StreamControlResponse:
    try:
        return market_stream_service.stop_stream(symbol)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/tick/{symbol}", response_model=TickMessage)
async def get_tick(symbol: str) -> TickMessage:
    try:
        return await _get_tick_with_timeout(symbol)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/clients")
async def get_clients() -> dict:
    return market_stream_service.get_clients()


@websocket_router.websocket("/ws/market/{symbol}")
async def stream_market_ticks(websocket: WebSocket, symbol: str) -> None:
    registered = False
    normalized_symbol = symbol.strip().upper() if symbol else ""
    try:
        if not normalized_symbol:
            await websocket.close(code=1008, reason="Symbol cannot be empty.")
            return
        if not market_stream_service.state.is_streaming(normalized_symbol):
            market_stream_service.start_stream(normalized_symbol)
        await market_stream_service.register_client(websocket, normalized_symbol)
        registered = True
        while market_stream_service.state.is_streaming(normalized_symbol):
            tick = await _get_tick_with_timeout(normalized_symbol)
            await websocket.send_json(tick.model_dump(mode="json"))
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass
    except Exception:
        if registered:
            await websocket.close(code=1011, reason="Streaming ended safely.")
    finally:
        if registered:
            market_stream_service.unregister_client(websocket, normalized_symbol)
