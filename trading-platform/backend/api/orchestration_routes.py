from fastapi import APIRouter, HTTPException, Query

from backend.orchestration.orchestration_models import PipelineResult
from backend.orchestration.orchestrator_service import OrchestratorService


router = APIRouter(prefix="/orchestration", tags=["Trading Orchestration"])
orchestrator_service = OrchestratorService()


@router.get("/status")
async def get_orchestration_status() -> dict:
    return orchestrator_service.get_orchestration_status()


@router.post("/run/{symbol}", response_model=PipelineResult)
async def run_symbol_pipeline(
    symbol: str,
    timeframe: str = Query(default="M15"),
) -> PipelineResult:
    try:
        return orchestrator_service.run_symbol_pipeline(symbol, timeframe)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/symbols")
async def get_monitored_symbols() -> dict:
    return {"symbols": orchestrator_service.get_monitored_symbols()}


@router.post("/symbols/{symbol}")
async def add_monitored_symbol(symbol: str) -> dict:
    try:
        return {"symbols": orchestrator_service.add_monitored_symbol(symbol)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/symbols/{symbol}")
async def remove_monitored_symbol(symbol: str) -> dict:
    try:
        return {"symbols": orchestrator_service.remove_monitored_symbol(symbol)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/last-decision/{symbol}")
async def get_last_decision(symbol: str) -> dict:
    decision = orchestrator_service.get_last_decision(symbol)
    if decision is None:
        raise HTTPException(status_code=404, detail="No orchestration decision is available for this symbol.")
    return decision.model_dump(mode="json")


@router.get("/config")
async def get_orchestration_config() -> dict:
    return orchestrator_service.symbol_monitor.get_config().model_dump(mode="json")
