from datetime import datetime, timezone

from fastapi import APIRouter

from backend.mt5_demo.mt5_market_data_service import MT5MarketDataService


router = APIRouter(prefix="/market-scope", tags=["Client Market Scope"])
market_data_service = MT5MarketDataService()


@router.get("/instruments/status")
async def get_scoped_instrument_status() -> list[dict]:
    return [
        _mt5_status("EURUSD"),
        _mt5_status("XAUUSD"),
        {
            "symbol": "NIFTY50",
            "enabled": False,
            "source": "PENDING_INDIAN_MARKET_INTEGRATION",
            "status": "INTEGRATION_PENDING",
            "message": "Indian market data/broker integration pending.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
        },
    ]


def _mt5_status(symbol: str) -> dict:
    tick = market_data_service.get_symbol_tick(symbol)
    status = "OPEN" if tick.get("status") == "OK" else "CLOSED"
    if tick.get("status") in {"MT5_UNAVAILABLE", "SYMBOL_NOT_AVAILABLE", "INVALID_SYMBOL"}:
        status = "OFFLINE"
    return {
        "symbol": symbol,
        "enabled": True,
        "source": "MT5_DEMO",
        "status": status,
        "bid": tick.get("bid"),
        "ask": tick.get("ask"),
        "spread": tick.get("spread"),
        "timestamp": tick.get("timestamp"),
        "message": tick.get("message"),
        "live_execution_enabled": False,
        "broker_execution_enabled": False,
        "execution_allowed": False,
    }
