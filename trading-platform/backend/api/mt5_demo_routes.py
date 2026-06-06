from typing import Any

from fastapi import APIRouter, Body

from backend.mt5_demo.demo_order_authorization_service import DemoOrderAuthorizationService
from backend.mt5_demo.demo_order_dry_run_service import DemoOrderDryRunService
from backend.mt5_demo.market_snapshot_service import MarketSnapshotService
from backend.mt5_demo.mt5_demo_service import MT5DemoService
from backend.mt5_demo.mt5_historical_backfill_service import MT5HistoricalBackfillService
from backend.mt5_demo.mt5_market_data_service import MT5MarketDataService
from backend.mt5_demo.mt5_strategy_consumption_service import MT5StrategyConsumptionService
from backend.mt5_demo.mt5_strategy_feed_adapter import MT5StrategyFeedAdapter
from backend.mt5_demo.mt5_risk_qualification_service import MT5RiskQualificationService
from backend.mt5_demo.mt5_execution_gate_validation_service import MT5ExecutionGateValidationService


router = APIRouter(prefix="/mt5-demo", tags=["MT5 Demo"])
service = MT5DemoService()
demo_order_authorization_service = DemoOrderAuthorizationService()
market_data_service = MT5MarketDataService()
market_snapshot_service = MarketSnapshotService(market_data_service=market_data_service)
historical_backfill_service = MT5HistoricalBackfillService(market_data_service=market_data_service)
strategy_feed_adapter = MT5StrategyFeedAdapter(backfill_service=historical_backfill_service)
strategy_consumption_service = MT5StrategyConsumptionService(feed_adapter=strategy_feed_adapter)
risk_qualification_service = MT5RiskQualificationService(strategy_consumption_service=strategy_consumption_service)
execution_gate_service = MT5ExecutionGateValidationService(
    risk_qualification_service=risk_qualification_service,
    market_snapshot_service=market_snapshot_service,
    backfill_service=historical_backfill_service,
)
demo_order_dry_run_service = DemoOrderDryRunService(
    authorization_service=demo_order_authorization_service,
    execution_gate_service=execution_gate_service,
)


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


@router.get("/strategy-consumption/status")
async def get_mt5_demo_strategy_consumption_status() -> dict:
    return strategy_consumption_service.get_status()


@router.post("/strategy-consumption/{symbol}/analyze")
async def analyze_mt5_demo_strategy_consumption(symbol: str) -> dict:
    return strategy_consumption_service.analyze_symbol_from_mt5_feed(symbol)


@router.post("/strategy-consumption/analyze-all")
async def analyze_all_mt5_demo_strategy_consumption() -> dict:
    return strategy_consumption_service.analyze_all_symbols_from_mt5_feed()


@router.get("/strategy-consumption/{symbol}/latest")
async def get_latest_mt5_demo_strategy_consumption(symbol: str) -> dict:
    return strategy_consumption_service.latest(symbol)


@router.get("/strategy-consumption/history")
async def get_mt5_demo_strategy_consumption_history(limit: int = 100) -> list[dict]:
    return strategy_consumption_service.history(limit)


@router.get("/risk-qualification/status")
async def get_mt5_demo_risk_qualification_status() -> dict:
    return risk_qualification_service.get_status()


@router.post("/risk-qualification/{symbol}/evaluate")
async def evaluate_mt5_demo_risk_qualification(symbol: str) -> dict:
    return risk_qualification_service.qualify_symbol_from_mt5_strategy(symbol)


@router.post("/risk-qualification/evaluate-all")
async def evaluate_all_mt5_demo_risk_qualification() -> dict:
    return risk_qualification_service.qualify_all_symbols_from_mt5_strategy()


@router.get("/risk-qualification/{symbol}/latest")
async def get_latest_mt5_demo_risk_qualification(symbol: str) -> dict:
    return risk_qualification_service.get_latest_risk_result(symbol)


@router.get("/risk-qualification/history")
async def get_mt5_demo_risk_qualification_history(limit: int = 100) -> list[dict]:
    return risk_qualification_service.history(limit)


@router.get("/execution-gate/status")
async def get_mt5_demo_execution_gate_status() -> dict:
    return execution_gate_service.get_status()


@router.post("/execution-gate/{symbol}/evaluate")
async def evaluate_mt5_demo_execution_gate(symbol: str) -> dict:
    return execution_gate_service.evaluate_symbol(symbol)


@router.post("/execution-gate/evaluate-all")
async def evaluate_all_mt5_demo_execution_gate() -> dict:
    return execution_gate_service.evaluate_all()


@router.get("/execution-gate/{symbol}/latest")
async def get_latest_mt5_demo_execution_gate(symbol: str) -> dict:
    return execution_gate_service.latest(symbol)


@router.get("/execution-gate/history")
async def get_mt5_demo_execution_gate_history(limit: int = 100) -> list[dict]:
    return execution_gate_service.history(limit)


@router.get("/pipeline-summary")
async def get_mt5_demo_pipeline_summary() -> dict:
    return execution_gate_service.pipeline_summary()


@router.get("/demo-authorization/status")
async def get_demo_order_authorization_status() -> dict:
    return demo_order_authorization_service.get_status()


@router.post("/demo-authorization/request")
async def request_demo_order_authorization(payload: dict[str, Any] = Body(default_factory=dict)) -> dict:
    return demo_order_authorization_service.request_demo_authorization(payload)


@router.post("/demo-authorization/revoke")
async def revoke_demo_order_authorization() -> dict:
    return demo_order_authorization_service.revoke_demo_authorization()


@router.get("/demo-authorization/checklist")
async def get_demo_order_authorization_checklist() -> dict:
    return demo_order_authorization_service.get_checklist()


@router.get("/demo-order-dry-run/status")
async def get_demo_order_dry_run_status() -> dict:
    return demo_order_dry_run_service.get_status()


@router.post("/demo-order-dry-run/create")
async def create_demo_order_dry_run(payload: dict[str, Any] = Body(default_factory=dict)) -> dict:
    return demo_order_dry_run_service.create_dry_run(payload)


@router.get("/demo-order-dry-run/latest")
async def get_latest_demo_order_dry_run() -> dict:
    return demo_order_dry_run_service.get_latest()


@router.get("/demo-order-dry-run/history")
async def get_demo_order_dry_run_history(limit: int = 100) -> list[dict]:
    return demo_order_dry_run_service.list_history(limit)


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
