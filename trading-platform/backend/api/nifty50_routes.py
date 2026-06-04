from fastapi import APIRouter

from backend.nifty50.indian_broker_registry import IndianBrokerRegistry
from backend.nifty50.nifty_execution_bridge import NIFTYExecutionBridge
from backend.nifty50.nifty_execution_models import NIFTYExecutionAuditEvent, NIFTYExecutionIntent, NIFTYOrderPreview
from backend.nifty50.nifty_order_mapper import NIFTYOrderMapper
from backend.nifty50.nifty_market_data_service import NIFTYMarketDataService
from backend.nifty50.nifty_market_data_models import NIFTYCandle, NIFTYMarketDataHealth, NIFTYTick
from backend.nifty50.nifty_models import NIFTY50Instrument, NIFTY50MarketDataSnapshot, NIFTY50ReadinessStatus
from backend.nifty50.nifty_readiness_service import NIFTYReadinessService
from backend.nifty50.nifty_risk_engine import NIFTYRiskEngine
from backend.nifty50.nifty_risk_models import NIFTYRiskDecision, NIFTYTradeCandidate
from backend.nifty50.nifty_strategy_models import (
    NIFTYFVGContext,
    NIFTYLiquidityContext,
    NIFTYOrderBlockContext,
    NIFTYStrategySnapshot,
    NIFTYStructureContext,
)
from backend.nifty50.nifty_strategy_service import NIFTYStrategyService
from backend.nifty50.nifty_trade_decision_store import NIFTYTradeDecisionStore
from backend.nifty50.nifty_trade_qualifier import NIFTYTradeQualifier


router = APIRouter(prefix="/nifty50", tags=["NIFTY50"])

broker_registry = IndianBrokerRegistry()
market_data_service = NIFTYMarketDataService(broker_registry=broker_registry)
readiness_service = NIFTYReadinessService(broker_registry=broker_registry)
strategy_service = NIFTYStrategyService(market_data_service=market_data_service)
decision_store = NIFTYTradeDecisionStore()
risk_engine = NIFTYRiskEngine()
trade_qualifier = NIFTYTradeQualifier(risk_engine=risk_engine, decision_store=decision_store)
execution_bridge = NIFTYExecutionBridge()
order_mapper = NIFTYOrderMapper()


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


@router.get("/risk/status")
async def get_nifty50_risk_status() -> dict:
    return {
        "status": "RISK_QUALIFICATION_READY",
        "symbol": "NIFTY50",
        "risk_ready": True,
        "execution_allowed": False,
        "simulation_only": True,
        "live_execution_enabled": False,
        "broker_execution_enabled": False,
    }


@router.post("/risk/evaluate", response_model=NIFTYRiskDecision)
async def evaluate_nifty50_risk() -> NIFTYRiskDecision:
    decision = risk_engine.evaluate(strategy_service.analyze())
    return decision_store.store_decision(decision)


@router.get("/risk/decisions", response_model=list[NIFTYRiskDecision])
async def list_nifty50_risk_decisions() -> list[NIFTYRiskDecision]:
    return decision_store.list_decisions()


@router.get("/risk/decisions/{decision_id}", response_model=NIFTYRiskDecision | None)
async def get_nifty50_risk_decision(decision_id: str) -> NIFTYRiskDecision | None:
    return decision_store.get_decision(decision_id)


@router.post("/trade/qualify", response_model=NIFTYTradeCandidate)
async def qualify_nifty50_trade() -> NIFTYTradeCandidate:
    return trade_qualifier.qualify(strategy_service.analyze())


@router.get("/trade/candidates", response_model=list[NIFTYTradeCandidate])
async def list_nifty50_trade_candidates() -> list[NIFTYTradeCandidate]:
    return decision_store.list_candidates()


@router.get("/execution/status")
async def get_nifty50_execution_status() -> dict:
    return execution_bridge.get_status()


@router.post("/execution/create-intent", response_model=NIFTYExecutionIntent)
async def create_nifty50_execution_intent() -> NIFTYExecutionIntent:
    candidate = trade_qualifier.qualify(strategy_service.analyze())
    return execution_bridge.create_intent_from_candidate(candidate)


@router.post("/execution/preview-order", response_model=NIFTYOrderPreview)
async def preview_nifty50_order() -> NIFTYOrderPreview:
    candidate = trade_qualifier.qualify(strategy_service.analyze())
    intent = execution_bridge.create_intent_from_candidate(candidate)
    return execution_bridge.preview_order(intent)


@router.get("/execution/intents", response_model=list[NIFTYExecutionIntent])
async def list_nifty50_execution_intents() -> list[NIFTYExecutionIntent]:
    return execution_bridge.store.list_intents()


@router.get("/execution/intents/{intent_id}", response_model=NIFTYExecutionIntent | None)
async def get_nifty50_execution_intent(intent_id: str) -> NIFTYExecutionIntent | None:
    return execution_bridge.store.get_intent(intent_id)


@router.get("/execution/previews", response_model=list[NIFTYOrderPreview])
async def list_nifty50_execution_previews() -> list[NIFTYOrderPreview]:
    return execution_bridge.list_previews()


@router.get("/execution/previews/{preview_id}", response_model=NIFTYOrderPreview | None)
async def get_nifty50_execution_preview(preview_id: str) -> NIFTYOrderPreview | None:
    return execution_bridge.get_preview(preview_id)


@router.get("/execution/audit-events", response_model=list[NIFTYExecutionAuditEvent])
async def list_nifty50_execution_audit_events() -> list[NIFTYExecutionAuditEvent]:
    return execution_bridge.store.list_audit_events()
