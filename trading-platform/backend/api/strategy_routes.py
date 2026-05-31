from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query

from backend.strategy_engine.session_manager import SessionManager
from backend.strategy_engine.strategy_service import StrategyService


router = APIRouter(prefix="/strategy", tags=["Strategy"])


def _service_unavailable(exc: Exception) -> HTTPException:
    return HTTPException(status_code=503, detail=str(exc))


@router.get("/status")
async def get_strategy_status() -> dict:
    service = StrategyService()
    try:
        return service.get_status()
    finally:
        service.close()


@router.post("/analyze/xauusd")
async def analyze_xauusd(payload: dict[str, Any] | None = Body(default=None)) -> dict:
    service = StrategyService()
    try:
        candles = payload.get("candles") if payload else None
        signal = service.analyze_xauusd(candles=candles)
        return signal.model_dump(mode="json")
    finally:
        service.close()


@router.get("/analyze/eurusd")
async def analyze_eurusd() -> dict:
    service = StrategyService()
    try:
        signal = service.analyze_eurusd()
        return signal.model_dump(mode="json")
    finally:
        service.close()


@router.post("/analyze/eurusd")
async def analyze_eurusd_with_payload(payload: dict[str, Any] | None = Body(default=None)) -> dict:
    service = StrategyService()
    try:
        candles = payload.get("candles") if payload else None
        signal = service.analyze_eurusd(candles=candles)
        return signal.model_dump(mode="json")
    finally:
        service.close()


@router.get("/eurusd/session-context")
async def get_eurusd_session_context() -> dict:
    service = StrategyService()
    try:
        return service.get_eurusd_session_context().model_dump(mode="json")
    finally:
        service.close()


@router.get("/eurusd/indicator-context")
async def get_eurusd_indicator_context() -> dict:
    service = StrategyService()
    try:
        return service.get_eurusd_indicator_context().model_dump(mode="json")
    finally:
        service.close()


@router.get("/eurusd/liquidity")
async def get_eurusd_liquidity_context() -> dict:
    service = StrategyService()
    try:
        return service.analyze_eurusd_liquidity().model_dump(mode="json")
    finally:
        service.close()


@router.post("/eurusd/liquidity/analyze")
async def analyze_eurusd_liquidity(payload: dict[str, Any] | None = Body(default=None)) -> dict:
    service = StrategyService()
    try:
        candles = payload.get("candles") if payload else None
        return service.analyze_eurusd_liquidity(candles=candles).model_dump(mode="json")
    finally:
        service.close()


@router.get("/signals")
async def list_strategy_signals(limit: int = Query(default=100, ge=1, le=1000)) -> list[dict]:
    service = StrategyService()
    try:
        return [signal.model_dump(mode="json") for signal in service.list_signals(limit)]
    finally:
        service.close()


@router.get("/signals/{signal_id}")
async def get_strategy_signal(signal_id: str) -> dict:
    service = StrategyService()
    try:
        signal = service.get_signal(signal_id)
        if signal is None:
            raise HTTPException(status_code=404, detail="Strategy signal not found.")
        return signal.model_dump(mode="json")
    finally:
        service.close()


@router.get("/session-context")
async def get_phase6_session_context() -> dict:
    service = StrategyService()
    try:
        return service.get_session_context().model_dump(mode="json")
    finally:
        service.close()


@router.get("/liquidity/xauusd")
async def get_xauusd_liquidity_context() -> dict:
    service = StrategyService()
    try:
        return service.analyze_xauusd_liquidity().model_dump(mode="json")
    finally:
        service.close()


@router.post("/liquidity/xauusd/analyze")
async def analyze_xauusd_liquidity(payload: dict[str, Any] | None = Body(default=None)) -> dict:
    service = StrategyService()
    try:
        candles = payload.get("candles") if payload else None
        return service.analyze_xauusd_liquidity(candles=candles).model_dump(mode="json")
    finally:
        service.close()


@router.get("/structure/xauusd")
async def get_xauusd_structure_context() -> dict:
    service = StrategyService()
    try:
        return service.analyze_xauusd_structure().model_dump(mode="json")
    finally:
        service.close()


@router.post("/structure/xauusd/analyze")
async def analyze_xauusd_structure(payload: dict[str, Any] | None = Body(default=None)) -> dict:
    service = StrategyService()
    try:
        candles = payload.get("candles") if payload else None
        return service.analyze_xauusd_structure(candles=candles).model_dump(mode="json")
    finally:
        service.close()


@router.get("/fvg/xauusd")
async def get_xauusd_fvg_context() -> dict:
    service = StrategyService()
    try:
        return service.analyze_xauusd_fvg()
    finally:
        service.close()


@router.post("/fvg/xauusd/analyze")
async def analyze_xauusd_fvg(payload: dict[str, Any] | None = Body(default=None)) -> dict:
    service = StrategyService()
    try:
        candles = payload.get("candles") if payload else None
        return service.analyze_xauusd_fvg(candles=candles)
    finally:
        service.close()


@router.get("/order-block/xauusd")
async def get_xauusd_order_block_context() -> dict:
    service = StrategyService()
    try:
        return service.analyze_xauusd_order_block()
    finally:
        service.close()


@router.post("/order-block/xauusd/analyze")
async def analyze_xauusd_order_block(payload: dict[str, Any] | None = Body(default=None)) -> dict:
    service = StrategyService()
    try:
        candles = payload.get("candles") if payload else None
        return service.analyze_xauusd_order_block(candles=candles)
    finally:
        service.close()


@router.get("/regime/xauusd")
async def get_xauusd_regime_context() -> dict:
    service = StrategyService()
    try:
        return service.analyze_xauusd_regime()
    finally:
        service.close()


@router.post("/regime/xauusd/analyze")
async def analyze_xauusd_regime(payload: dict[str, Any] | None = Body(default=None)) -> dict:
    service = StrategyService()
    try:
        candles = payload.get("candles") if payload else None
        return service.analyze_xauusd_regime(candles=candles)
    finally:
        service.close()


@router.get("/confluence/xauusd")
async def get_xauusd_confluence_context() -> dict:
    service = StrategyService()
    try:
        return service.analyze_xauusd_confluence()
    finally:
        service.close()


@router.post("/confluence/xauusd/analyze")
async def analyze_xauusd_confluence(payload: dict[str, Any] | None = Body(default=None)) -> dict:
    service = StrategyService()
    try:
        candles = payload.get("candles") if payload else None
        return service.analyze_xauusd_confluence(candles=candles)
    finally:
        service.close()


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
