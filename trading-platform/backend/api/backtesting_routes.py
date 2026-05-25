from fastapi import APIRouter, Body, HTTPException, Query

from backend.backtesting.backtest_models import BacktestRequest, BacktestResult
from backend.backtesting.backtest_service import BacktestService


router = APIRouter(prefix="/backtesting", tags=["Backtesting Engine"])
backtest_service = BacktestService()


@router.get("/status")
async def get_backtesting_status() -> dict:
    return backtest_service.get_status()


@router.post("/run/{symbol}", response_model=BacktestResult)
async def run_backtest(
    symbol: str,
    request: BacktestRequest | None = Body(default=None),
) -> BacktestResult:
    try:
        configured_request = (request or BacktestRequest()).model_copy(
            update={"symbol": symbol.strip().upper()}
        )
        configured_request = BacktestRequest.model_validate(configured_request.model_dump())
        return backtest_service.run_backtest(configured_request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/results/recent", response_model=list[BacktestResult])
async def get_recent_results(limit: int = Query(default=50, ge=1, le=500)) -> list[BacktestResult]:
    return backtest_service.get_recent_results(limit)


@router.get("/result/{backtest_id}", response_model=BacktestResult)
async def get_result(backtest_id: str) -> BacktestResult:
    result = backtest_service.get_result(backtest_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Backtest result not found.")
    return result


@router.get("/metrics/{backtest_id}")
async def get_metrics(backtest_id: str) -> dict:
    metrics = backtest_service.get_metrics(backtest_id)
    if metrics is None:
        raise HTTPException(status_code=404, detail="Backtest result not found.")
    return metrics.model_dump(mode="json")


@router.get("/equity/{backtest_id}")
async def get_equity_curve(backtest_id: str) -> list[dict]:
    curve = backtest_service.get_equity_curve(backtest_id)
    if curve is None:
        raise HTTPException(status_code=404, detail="Backtest result not found.")
    return curve
