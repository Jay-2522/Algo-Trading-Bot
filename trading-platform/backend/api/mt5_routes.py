from fastapi import APIRouter, HTTPException

from backend.broker_integrations.mt5.mt5_account_service import MT5AccountService
from backend.broker_integrations.mt5.mt5_connection_manager import MT5ConnectionManager
from backend.broker_integrations.mt5.mt5_data_models import (
    MT5AccountInfo,
    MT5ConnectionStatus,
    MT5HealthStatus,
    MT5PositionInfo,
    MT5SymbolInfo,
    MT5TickInfo,
)
from backend.broker_integrations.mt5.mt5_health_service import MT5HealthService
from backend.broker_integrations.mt5.mt5_position_service import MT5PositionService
from backend.broker_integrations.mt5.mt5_symbol_service import MT5SymbolService
from backend.broker_integrations.mt5.mt5_tick_service import MT5TickService


router = APIRouter(prefix="/mt5", tags=["MT5 Broker Data"])
connection_manager = MT5ConnectionManager()
account_service = MT5AccountService(connection_manager)
symbol_service = MT5SymbolService(connection_manager)
tick_service = MT5TickService(connection_manager)
position_service = MT5PositionService(connection_manager)
health_service = MT5HealthService(connection_manager)


@router.get("/status", response_model=MT5ConnectionStatus)
async def get_mt5_status() -> MT5ConnectionStatus:
    return connection_manager.get_connection_status()


@router.post("/initialize", response_model=MT5ConnectionStatus)
async def initialize_mt5() -> MT5ConnectionStatus:
    return connection_manager.initialize()


@router.post("/shutdown", response_model=MT5ConnectionStatus)
async def shutdown_mt5() -> MT5ConnectionStatus:
    return connection_manager.shutdown()


@router.get("/account", response_model=MT5AccountInfo)
async def get_account_info() -> MT5AccountInfo:
    return account_service.get_account_info()


@router.get("/symbol/{symbol}", response_model=MT5SymbolInfo)
async def get_symbol_info(symbol: str) -> MT5SymbolInfo:
    try:
        return symbol_service.ensure_symbol_visible(symbol)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/tick/{symbol}", response_model=MT5TickInfo)
async def get_latest_tick(symbol: str) -> MT5TickInfo:
    try:
        return tick_service.get_latest_tick(symbol)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/positions", response_model=list[MT5PositionInfo])
async def get_open_positions() -> list[MT5PositionInfo]:
    return position_service.get_open_positions()


@router.get("/positions/{symbol}", response_model=list[MT5PositionInfo])
async def get_positions_by_symbol(symbol: str) -> list[MT5PositionInfo]:
    try:
        return position_service.get_positions_by_symbol(symbol)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/health", response_model=MT5HealthStatus)
async def get_mt5_health() -> MT5HealthStatus:
    return health_service.get_health_status()

