from fastapi import APIRouter, Body, HTTPException, Query

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
