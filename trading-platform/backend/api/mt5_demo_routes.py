from fastapi import APIRouter

from backend.mt5_demo.market_snapshot_service import MarketSnapshotService
from backend.mt5_demo.mt5_demo_service import MT5DemoService
from backend.mt5_demo.mt5_market_data_service import MT5MarketDataService


router = APIRouter(prefix="/mt5-demo", tags=["MT5 Demo"])
service = MT5DemoService()
market_data_service = MT5MarketDataService()
market_snapshot_service = MarketSnapshotService(market_data_service=market_data_service)


@router.get("/status")
async def get_mt5_demo_status() -> dict:
    return service.get_status()


@router.get("/account")
async def get_mt5_demo_account() -> dict:
    return service.get_account()


@router.get("/symbols")
async def get_mt5_demo_symbols() -> dict:
    return service.get_symbols()


@router.get("/health")
async def get_mt5_demo_health() -> dict:
    return service.get_health()


@router.get("/market-watch")
async def get_mt5_demo_market_watch() -> dict:
    return service.get_market_watch()


@router.get("/overview")
async def get_mt5_demo_overview() -> dict:
    return market_snapshot_service.get_overview()


@router.get("/market-data/status")
async def get_mt5_demo_market_data_status() -> dict:
    return market_data_service.get_market_data_status()


@router.get("/market-data/tick/{symbol}")
async def get_mt5_demo_symbol_tick(symbol: str) -> dict:
    return market_data_service.get_symbol_tick(symbol)


@router.get("/market-data/candles/{symbol}/{timeframe}")
async def get_mt5_demo_symbol_candles(symbol: str, timeframe: str, count: int = 50) -> dict:
    return market_data_service.get_symbol_candles(symbol, timeframe, count)


@router.get("/market-data/spread/{symbol}")
async def get_mt5_demo_symbol_spread(symbol: str) -> dict:
    return market_data_service.get_symbol_spread(symbol)


@router.post("/order-send")
async def block_order_send() -> dict:
    return service.block_execution_attempt("order_send")


@router.post("/position-open")
async def block_position_open() -> dict:
    return service.block_execution_attempt("position_open")


@router.post("/market-buy")
async def block_market_buy() -> dict:
    return service.block_execution_attempt("market_buy")


@router.post("/market-sell")
async def block_market_sell() -> dict:
    return service.block_execution_attempt("market_sell")
