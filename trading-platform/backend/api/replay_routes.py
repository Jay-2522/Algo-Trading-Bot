from fastapi import APIRouter, Body, HTTPException, Query

from backend.replay.replay_models import ReplayRequest, ReplayRunResult, ReplayStatus
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
