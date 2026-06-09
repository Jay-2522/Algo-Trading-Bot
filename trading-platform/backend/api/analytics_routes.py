from backend.analytics.performance_validation_service import PerformanceValidationService
from backend.analytics.risk_alert_service import RiskAlertService
from backend.analytics.strategy_health_monitor_service import StrategyHealthMonitorService
from backend.analytics.trade_outcome_intelligence_service import TradeOutcomeIntelligenceService

from fastapi import APIRouter


router = APIRouter(prefix="/analytics", tags=["Trade Outcome Analytics"])
trade_outcome_intelligence_service = TradeOutcomeIntelligenceService()
performance_validation_service = PerformanceValidationService()
strategy_health_monitor_service = StrategyHealthMonitorService(validation=performance_validation_service)
risk_alert_service = RiskAlertService(validation=performance_validation_service, health_monitor=strategy_health_monitor_service)


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


@router.get("/strategy-health/status")
async def get_strategy_health_status() -> dict:
    return strategy_health_monitor_service.get_status()


@router.get("/strategy-health/current")
async def get_current_strategy_health() -> dict:
    return strategy_health_monitor_service.get_current_health()


@router.get("/strategy-health/history")
async def get_strategy_health_history() -> dict:
    return strategy_health_monitor_service.get_history()


@router.get("/risk-alerts/status")
async def get_risk_alerts_status() -> dict:
    return risk_alert_service.get_status()


@router.get("/risk-alerts/current")
async def get_current_risk_alerts() -> dict:
    return risk_alert_service.get_current_alerts()


@router.get("/risk-alerts/history")
async def get_risk_alerts_history() -> dict:
    return risk_alert_service.get_history()
