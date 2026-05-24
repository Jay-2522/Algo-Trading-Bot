from fastapi import APIRouter, HTTPException, Query

from backend.strategy_engine.session_manager import SessionManager
from backend.strategy_engine.strategy_service import StrategyService


router = APIRouter(prefix="/strategy", tags=["Strategy"])


def _service_unavailable(exc: Exception) -> HTTPException:
    return HTTPException(status_code=503, detail=str(exc))


@router.get("/trend/{symbol}")
async def get_trend_analysis(symbol: str, timeframe: str = Query(default="M15")) -> dict:
    service = StrategyService()
    try:
        analysis = service.analyze_symbol(symbol, timeframe)
        return {
            "symbol": analysis["symbol"],
            "timeframe": analysis["timeframe"],
            "trend_analysis": analysis["trend_analysis"],
            "status": analysis["status"],
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise _service_unavailable(exc) from exc
    finally:
        service.close()


@router.get("/liquidity/{symbol}")
async def get_liquidity_analysis(symbol: str, timeframe: str = Query(default="M15")) -> dict:
    service = StrategyService()
    try:
        analysis = service.analyze_symbol(symbol, timeframe)
        return {
            "symbol": analysis["symbol"],
            "timeframe": analysis["timeframe"],
            "liquidity_analysis": analysis["liquidity_analysis"],
            "status": analysis["status"],
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise _service_unavailable(exc) from exc
    finally:
        service.close()


@router.get("/structure/{symbol}")
async def get_structure_analysis(symbol: str, timeframe: str = Query(default="M15")) -> dict:
    service = StrategyService()
    try:
        analysis = service.analyze_symbol(symbol, timeframe)
        return {
            "symbol": analysis["symbol"],
            "timeframe": analysis["timeframe"],
            "structure_analysis": analysis["structure_analysis"],
            "status": analysis["status"],
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise _service_unavailable(exc) from exc
    finally:
        service.close()


@router.get("/session")
async def get_session_info() -> dict:
    return SessionManager().get_session_info()


@router.get("/snapshot/{symbol}")
async def get_strategy_snapshot(symbol: str, timeframe: str = Query(default="M15")) -> dict:
    service = StrategyService()
    try:
        snapshot = service.get_strategy_snapshot(symbol, timeframe)
        return snapshot.to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise _service_unavailable(exc) from exc
    finally:
        service.close()
