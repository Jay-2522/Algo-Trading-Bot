from fastapi import APIRouter

from backend.mt5_demo.market_snapshot_service import MarketSnapshotService
from backend.mt5_demo.mt5_demo_service import MT5DemoService
from backend.mt5_demo.mt5_historical_backfill_service import MT5HistoricalBackfillService
from backend.mt5_demo.mt5_market_data_service import MT5MarketDataService
from backend.mt5_demo.mt5_strategy_feed_adapter import MT5StrategyFeedAdapter


router = APIRouter(prefix="/mt5-demo", tags=["MT5 Demo"])
service = MT5DemoService()
market_data_service = MT5MarketDataService()
market_snapshot_service = MarketSnapshotService(market_data_service=market_data_service)
historical_backfill_service = MT5HistoricalBackfillService(market_data_service=market_data_service)
strategy_feed_adapter = MT5StrategyFeedAdapter(backfill_service=historical_backfill_service)


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


@router.get("/history/status")
async def get_mt5_demo_history_status() -> dict:
    return historical_backfill_service.get_status()


@router.get("/history/{symbol}/{timeframe}")
async def get_mt5_demo_history(symbol: str, timeframe: str, count: int = 500) -> dict:
    return historical_backfill_service.fetch_history(symbol, timeframe, count)


@router.get("/history/{symbol}/{timeframe}/summary")
async def get_mt5_demo_history_summary(symbol: str, timeframe: str) -> dict:
    return historical_backfill_service.summarize_backfill(symbol, timeframe)


@router.get("/history/{symbol}/{timeframe}/validate")
async def validate_mt5_demo_history(symbol: str, timeframe: str, count: int = 500) -> dict:
    history = historical_backfill_service.fetch_history(symbol, timeframe, count)
    return {
        "symbol": history.get("symbol"),
        "timeframe": history.get("timeframe"),
        "requested_count": history.get("requested_count"),
        "returned_count": history.get("returned_count"),
        "validation": history.get("validation"),
        "status": history.get("status"),
        "source": "MT5_DEMO",
        "simulation_only": True,
        "live_execution_enabled": False,
        "broker_execution_enabled": False,
        "execution_allowed": False,
    }


@router.get("/strategy-feed/{symbol}")
async def get_mt5_demo_strategy_feed(symbol: str) -> dict:
    return strategy_feed_adapter.build_strategy_feed(symbol)


@router.get("/strategy-feed/{symbol}/htf")
async def get_mt5_demo_strategy_feed_htf(symbol: str) -> dict:
    return strategy_feed_adapter.get_htf_context(symbol)


@router.get("/strategy-feed/{symbol}/ltf")
async def get_mt5_demo_strategy_feed_ltf(symbol: str) -> dict:
    return strategy_feed_adapter.get_ltf_context(symbol)


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
