from fastapi import APIRouter

from backend.nifty50.indian_broker_registry import IndianBrokerRegistry
from backend.nifty50.nifty_market_data_service import NIFTYMarketDataService
from backend.nifty50.nifty_market_data_models import NIFTYCandle, NIFTYMarketDataHealth, NIFTYTick
from backend.nifty50.nifty_models import NIFTY50Instrument, NIFTY50MarketDataSnapshot, NIFTY50ReadinessStatus
from backend.nifty50.nifty_readiness_service import NIFTYReadinessService
from backend.nifty50.nifty_strategy_models import (
    NIFTYFVGContext,
    NIFTYLiquidityContext,
    NIFTYOrderBlockContext,
    NIFTYStrategySnapshot,
    NIFTYStructureContext,
)
from backend.nifty50.nifty_strategy_service import NIFTYStrategyService


router = APIRouter(prefix="/nifty50", tags=["NIFTY50"])

broker_registry = IndianBrokerRegistry()
market_data_service = NIFTYMarketDataService(broker_registry=broker_registry)
readiness_service = NIFTYReadinessService(broker_registry=broker_registry)
strategy_service = NIFTYStrategyService(market_data_service=market_data_service)


@router.get("/status")
async def get_nifty50_status() -> dict:
    status = market_data_service.get_status()
    status["readiness"] = readiness_service.get_status().model_dump(mode="json")
    return status


@router.get("/instrument", response_model=NIFTY50Instrument)
async def get_nifty50_instrument() -> NIFTY50Instrument:
    return market_data_service.get_instrument()


@router.get("/brokers")
async def get_nifty50_brokers() -> list[dict]:
    return market_data_service.get_broker_candidates()


@router.get("/brokers/recommended")
async def get_nifty50_recommended_brokers() -> dict:
    return broker_registry.get_recommended_broker()


@router.get("/session")
async def get_nifty50_session() -> dict:
    return market_data_service.get_session_context()


@router.get("/market-data/snapshot", response_model=NIFTY50MarketDataSnapshot)
async def get_nifty50_market_data_snapshot() -> NIFTY50MarketDataSnapshot:
    return market_data_service.get_snapshot()


@router.get("/market-data/status")
async def get_nifty50_market_data_status() -> dict:
    return market_data_service.get_status()


@router.get("/market-data/health", response_model=NIFTYMarketDataHealth)
async def get_nifty50_market_data_health() -> NIFTYMarketDataHealth:
    return market_data_service.get_health()


@router.get("/market-data/timeframes")
async def get_nifty50_market_data_timeframes() -> dict:
    return {
        "supported_timeframes": market_data_service.get_supported_timeframes(),
        "simulation_only": True,
        "live_execution_enabled": False,
        "broker_execution_enabled": False,
    }


@router.get("/market-data/latest")
async def get_nifty50_market_data_latest() -> dict:
    return market_data_service.get_latest()


@router.post("/market-data/ingest-candle")
async def ingest_nifty50_candle(candle: NIFTYCandle) -> dict:
    return market_data_service.ingest_candle(candle)


@router.post("/market-data/ingest-tick")
async def ingest_nifty50_tick(tick: NIFTYTick) -> dict:
    return market_data_service.ingest_tick(tick)


@router.get("/readiness", response_model=NIFTY50ReadinessStatus)
async def get_nifty50_readiness() -> NIFTY50ReadinessStatus:
    return readiness_service.get_status()


@router.get("/blockers")
async def get_nifty50_blockers() -> dict:
    return {
        "blockers": readiness_service.get_blockers(),
        "warnings": readiness_service.get_warnings(),
        "next_steps": readiness_service.get_next_steps(),
        "simulation_only": True,
        "live_execution_enabled": False,
        "broker_execution_enabled": False,
    }


@router.get("/strategy/status")
async def get_nifty50_strategy_status() -> dict:
    return strategy_service.get_status()


@router.get("/strategy/liquidity", response_model=NIFTYLiquidityContext)
async def get_nifty50_strategy_liquidity() -> NIFTYLiquidityContext:
    return strategy_service.liquidity_service.get_snapshot()


@router.get("/strategy/structure", response_model=NIFTYStructureContext)
async def get_nifty50_strategy_structure() -> NIFTYStructureContext:
    return strategy_service.structure_service.get_snapshot()


@router.get("/strategy/fvg", response_model=NIFTYFVGContext)
async def get_nifty50_strategy_fvg() -> NIFTYFVGContext:
    return strategy_service.fvg_service.get_snapshot()


@router.get("/strategy/order-block", response_model=NIFTYOrderBlockContext)
async def get_nifty50_strategy_order_block() -> NIFTYOrderBlockContext:
    return strategy_service.order_block_service.get_snapshot()


@router.get("/strategy/snapshot", response_model=NIFTYStrategySnapshot)
async def get_nifty50_strategy_snapshot() -> NIFTYStrategySnapshot:
    return strategy_service.get_snapshot()


@router.get("/strategy/regime")
async def get_nifty50_strategy_regime() -> dict:
    snapshot = strategy_service.get_snapshot()
    return {
        "symbol": snapshot.symbol,
        "regime": snapshot.regime,
        "placeholder": snapshot.placeholder,
        "simulation_only": True,
        "live_execution_enabled": False,
        "broker_execution_enabled": False,
    }


@router.get("/strategy/confidence")
async def get_nifty50_strategy_confidence() -> dict:
    snapshot = strategy_service.get_snapshot()
    return {
        "symbol": snapshot.symbol,
        "confidence": snapshot.confidence,
        "placeholder": snapshot.placeholder,
        "simulation_only": True,
        "live_execution_enabled": False,
        "broker_execution_enabled": False,
    }


@router.get("/strategy/bias")
async def get_nifty50_strategy_bias() -> dict:
    snapshot = strategy_service.get_snapshot()
    return {
        "symbol": snapshot.symbol,
        "strategy_bias": snapshot.strategy_bias,
        "placeholder": snapshot.placeholder,
        "simulation_only": True,
        "live_execution_enabled": False,
        "broker_execution_enabled": False,
    }


@router.post("/strategy/analyze", response_model=NIFTYStrategySnapshot)
async def analyze_nifty50_strategy() -> NIFTYStrategySnapshot:
    return strategy_service.analyze()
