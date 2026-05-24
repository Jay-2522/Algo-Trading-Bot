from fastapi import APIRouter, HTTPException, Query

from backend.market_data.market_data_service import MarketDataService, build_snapshot
from backend.market_data.market_snapshot import MarketSnapshot
from backend.market_data.validators import (
    supported_timeframes,
    validate_candle_count,
    validate_symbol_name,
    validate_timeframe,
)


router = APIRouter(prefix="/market-data", tags=["market-data"])


def _service_unavailable(exc: Exception) -> HTTPException:
    return HTTPException(status_code=503, detail=str(exc))


@router.get("/timeframes")
async def get_supported_timeframes() -> dict:
    return {"timeframes": supported_timeframes()}


@router.get("/tick/{symbol}")
async def get_latest_tick(symbol: str) -> dict:
    service = MarketDataService()
    try:
        normalized_symbol = validate_symbol_name(symbol)
        return {
            "symbol": normalized_symbol,
            "latest_tick": service.get_latest_tick(normalized_symbol),
            "status": "ok",
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise _service_unavailable(exc) from exc
    finally:
        service.close()


@router.get("/candles/{symbol}")
async def get_candles(
    symbol: str,
    timeframe: str = Query(default="M15"),
    count: int = Query(default=100),
) -> dict:
    service = MarketDataService()
    try:
        normalized_symbol = validate_symbol_name(symbol)
        normalized_timeframe = validate_timeframe(timeframe)
        validated_count = validate_candle_count(count)
        candles = service.get_candles(normalized_symbol, normalized_timeframe, validated_count)
        return {
            "symbol": normalized_symbol,
            "timeframe": normalized_timeframe,
            "count": len(candles),
            "candles": [candle.to_dict() for candle in candles],
            "status": "ok",
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise _service_unavailable(exc) from exc
    finally:
        service.close()


@router.get("/snapshot/{symbol}")
async def get_market_snapshot(symbol: str) -> dict:
    service = MarketDataService()
    try:
        snapshot = MarketSnapshot(**build_snapshot(symbol, service=service))
        return snapshot.to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise _service_unavailable(exc) from exc
    finally:
        service.close()

