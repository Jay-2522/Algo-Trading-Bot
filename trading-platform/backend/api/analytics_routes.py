from backend.analytics.performance_validation_service import PerformanceValidationService
from backend.analytics.trade_outcome_intelligence_service import TradeOutcomeIntelligenceService

from fastapi import APIRouter


router = APIRouter(prefix="/analytics", tags=["Trade Outcome Analytics"])
trade_outcome_intelligence_service = TradeOutcomeIntelligenceService()
performance_validation_service = PerformanceValidationService()


@router.get("/outcomes/status")
async def get_outcomes_status() -> dict:
    return trade_outcome_intelligence_service.get_status()


@router.get("/outcomes/latest")
async def get_latest_outcome() -> dict:
    return trade_outcome_intelligence_service.get_latest()


@router.get("/outcomes/trades")
async def get_outcome_trades() -> list[dict]:
    return trade_outcome_intelligence_service.get_trades()


@router.get("/outcomes/symbols")
async def get_outcome_symbols() -> list[dict]:
    return trade_outcome_intelligence_service.get_symbol_performance()


@router.get("/outcomes/sessions")
async def get_outcome_sessions() -> list[dict]:
    return trade_outcome_intelligence_service.get_session_performance()


@router.get("/outcomes/summary")
async def get_outcome_summary() -> dict:
    return trade_outcome_intelligence_service.get_summary()


@router.get("/performance-validation/status")
async def get_performance_validation_status() -> dict:
    return performance_validation_service.get_status()


@router.get("/performance-validation/live")
async def get_live_performance_validation() -> dict:
    return performance_validation_service.get_live_performance()


@router.get("/performance-validation/historical")
async def get_historical_performance_validation() -> dict:
    return performance_validation_service.get_historical_performance()


@router.get("/performance-validation/compare")
async def compare_performance_validation() -> dict:
    return performance_validation_service.compare()


@router.get("/performance-validation/drift")
async def get_performance_validation_drift() -> dict:
    return performance_validation_service.detect_drift()
