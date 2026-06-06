from fastapi import APIRouter

from backend.mt5_demo.mt5_demo_service import MT5DemoService


router = APIRouter(prefix="/mt5-demo", tags=["MT5 Demo"])
service = MT5DemoService()


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
