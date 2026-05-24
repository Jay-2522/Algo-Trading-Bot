from fastapi import APIRouter, HTTPException

from backend.ai_engine.ai_orchestrator import AIOrchestrator
from backend.ai_engine.ai_models import TradeDecision


router = APIRouter(prefix="/ai", tags=["AI Decision Engine"])
orchestrator = AIOrchestrator()


def _analysis(symbol: str, persist: bool = False) -> dict:
    try:
        return orchestrator.generate_full_analysis(symbol, persist=persist)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/status")
async def get_ai_status() -> dict:
    return {
        "status": "operational",
        "model_type": "RULE_BASED_AI_FOUNDATION",
        "live_execution_enabled": False,
    }


@router.get("/regime/{symbol}")
async def get_market_regime(symbol: str) -> dict:
    return _analysis(symbol)["regime"].model_dump(mode="json")


@router.get("/signal-score/{symbol}")
async def get_signal_score(symbol: str) -> dict:
    return _analysis(symbol)["signal_score"].model_dump(mode="json")


@router.get("/decision/{symbol}", response_model=TradeDecision)
async def get_trade_decision(symbol: str) -> TradeDecision:
    result = _analysis(symbol, persist=True)
    return result["decision"]


@router.get("/full-analysis/{symbol}")
async def get_full_analysis(symbol: str) -> dict:
    result = _analysis(symbol, persist=True)
    return {
        "decision": result["decision"].model_dump(mode="json"),
        "explanation": result["explanation"].model_dump(mode="json"),
        "signal_score": result["signal_score"].model_dump(mode="json"),
        "regime": result["regime"].model_dump(mode="json"),
    }


@router.get("/confidence/{symbol}")
async def get_confidence(symbol: str) -> dict:
    decision = _analysis(symbol)["decision"]
    return {"symbol": decision.symbol, "confidence": decision.confidence}
