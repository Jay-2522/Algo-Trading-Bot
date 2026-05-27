from fastapi import APIRouter, Body, HTTPException, Query

from backend.replay.client_symbol_models import ClientInstrument, ClientSymbolResolution
from backend.replay.replay_calibration_models import (
    ReplayBlockReasonMetrics,
    ReplayCalibrationReport,
    ThresholdAdjustmentSuggestion,
)
from backend.replay.replay_comparison_models import (
    ReplayFilterComparison,
    ReplayScenarioComparison,
    ReplayTimeframeComparison,
)
from backend.replay.replay_models import ReplayRequest, ReplayRunResult, ReplayStatus
from backend.replay.replay_report_models import (
    ReplayDecisionAnalytics,
    ReplayEquityPoint,
    ReplayHistoricalReport,
    ReplayTradeAnalytics,
    ReplayWeaknessInsight,
)
from backend.replay.replay_service import ReplayService


router = APIRouter(prefix="/replay", tags=["Advanced Historical Replay"])
replay_service = ReplayService()


@router.get("/status", response_model=ReplayStatus)
async def get_replay_status() -> ReplayStatus:
    return replay_service.get_status()


@router.get("/symbols", response_model=list[ClientInstrument])
async def list_supported_replay_symbols() -> list[ClientInstrument]:
    return replay_service.list_supported_symbols()


@router.get("/symbols/{symbol}", response_model=ClientSymbolResolution)
async def resolve_replay_symbol(symbol: str) -> ClientSymbolResolution:
    return replay_service.resolve_symbol(symbol)


@router.post("/run/{symbol}", response_model=ReplayRunResult)
async def run_replay(
    symbol: str,
    timeframe: str = Query(default="M15"),
    request: ReplayRequest | None = Body(default=None),
) -> ReplayRunResult:
    try:
        return replay_service.run_replay(symbol, timeframe, request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/recent", response_model=list[ReplayRunResult])
async def get_recent_replays(limit: int = Query(default=20, ge=1, le=100)) -> list[ReplayRunResult]:
    return replay_service.get_recent_replays(limit)


@router.get("/result/{replay_id}", response_model=ReplayRunResult)
async def get_replay_result(replay_id: str) -> ReplayRunResult:
    result = replay_service.get_replay_result(replay_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Replay result not found.")
    return result


@router.get("/metrics/{replay_id}")
async def get_replay_metrics(replay_id: str) -> dict:
    result = replay_service.get_replay_result(replay_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Replay result not found.")
    return {
        "replay_id": result.replay_id,
        "symbol": result.symbol,
        "timeframe": result.timeframe,
        "total_steps": result.total_steps,
        "decisions_count": result.decisions_count,
        "simulated_trades_count": result.simulated_trades_count,
        "blocked_count": result.blocked_count,
        "wait_count": result.wait_count,
        "avoid_count": result.avoid_count,
        "win_count": result.win_count,
        "loss_count": result.loss_count,
        "breakeven_count": result.breakeven_count,
        "net_rr": result.net_rr,
        "max_drawdown": result.max_drawdown,
        "simulation_only": result.simulation_only,
        "live_execution_enabled": result.live_execution_enabled,
    }


@router.get("/report/latest", response_model=ReplayHistoricalReport)
async def get_latest_replay_report() -> ReplayHistoricalReport:
    return replay_service.get_latest_replay_report()


@router.get("/report/{replay_id}", response_model=ReplayHistoricalReport)
async def get_replay_report(replay_id: str) -> ReplayHistoricalReport:
    report = replay_service.get_replay_report(replay_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Replay report not found.")
    return report


@router.get("/analytics/trades/{replay_id}", response_model=ReplayTradeAnalytics)
async def get_replay_trade_analytics(replay_id: str) -> ReplayTradeAnalytics:
    report = replay_service.get_replay_report(replay_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Replay report not found.")
    return report.trade_analytics


@router.get("/analytics/decisions/{replay_id}", response_model=ReplayDecisionAnalytics)
async def get_replay_decision_analytics(replay_id: str) -> ReplayDecisionAnalytics:
    report = replay_service.get_replay_report(replay_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Replay report not found.")
    return report.decision_analytics


@router.get("/equity/{replay_id}", response_model=list[ReplayEquityPoint])
async def get_replay_equity_curve(replay_id: str) -> list[ReplayEquityPoint]:
    report = replay_service.get_replay_report(replay_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Replay report not found.")
    return report.equity_curve


@router.get("/weaknesses/{replay_id}", response_model=list[ReplayWeaknessInsight])
async def get_replay_weaknesses(replay_id: str) -> list[ReplayWeaknessInsight]:
    report = replay_service.get_replay_report(replay_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Replay report not found.")
    return report.weakness_insights


@router.get("/calibration/latest", response_model=ReplayCalibrationReport)
async def get_latest_replay_calibration() -> ReplayCalibrationReport:
    return replay_service.get_latest_replay_calibration()


@router.get("/calibration/{replay_id}", response_model=ReplayCalibrationReport)
async def get_replay_calibration(replay_id: str) -> ReplayCalibrationReport:
    calibration = replay_service.get_replay_calibration(replay_id)
    if calibration is None:
        raise HTTPException(status_code=404, detail="Replay calibration not found.")
    return calibration


@router.get("/calibration/block-reasons/{replay_id}", response_model=ReplayBlockReasonMetrics)
async def get_replay_calibration_block_reasons(replay_id: str) -> ReplayBlockReasonMetrics:
    calibration = replay_service.get_replay_calibration(replay_id)
    if calibration is None:
        raise HTTPException(status_code=404, detail="Replay calibration not found.")
    return calibration.block_reason_metrics


@router.get("/calibration/suggestions/{replay_id}", response_model=list[ThresholdAdjustmentSuggestion])
async def get_replay_calibration_suggestions(replay_id: str) -> list[ThresholdAdjustmentSuggestion]:
    calibration = replay_service.get_replay_calibration(replay_id)
    if calibration is None:
        raise HTTPException(status_code=404, detail="Replay calibration not found.")
    return calibration.threshold_suggestions


@router.get("/compare/recent", response_model=ReplayScenarioComparison)
async def compare_recent_replays(limit: int = Query(default=5, ge=1, le=50)) -> ReplayScenarioComparison:
    return replay_service.compare_recent_replays(limit)


@router.post("/compare", response_model=ReplayScenarioComparison)
async def compare_replay_ids(replay_ids: list[str] = Body(default_factory=list)) -> ReplayScenarioComparison:
    return replay_service.compare_replay_ids(replay_ids)


@router.get("/compare/timeframes/{symbol}", response_model=ReplayTimeframeComparison)
async def compare_replay_timeframes(symbol: str) -> ReplayTimeframeComparison:
    return replay_service.compare_timeframes(symbol)


@router.get("/compare/filters", response_model=ReplayFilterComparison)
async def compare_replay_filters() -> ReplayFilterComparison:
    return replay_service.compare_filters()


@router.post("/run-all-client-symbols")
async def run_all_client_symbols(timeframe: str = Query(default="M15")) -> dict:
    return replay_service.run_all_client_symbols(timeframe)


@router.get("/compare/client-symbols", response_model=ReplayScenarioComparison)
async def compare_client_symbols(timeframe: str = Query(default="M15")) -> ReplayScenarioComparison:
    return replay_service.compare_client_symbols(timeframe)
