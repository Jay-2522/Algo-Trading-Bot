from fastapi import APIRouter

from backend.strategy.client_signal_engine import ClientSignalEngine


router = APIRouter(prefix="/client-signals-engine", tags=["Client Signal Engine"])
client_signal_engine = ClientSignalEngine()


@router.get("/status")
async def get_client_signal_engine_status() -> dict:
    return client_signal_engine.status()


@router.get("/current")
async def get_current_client_signal_engine_signals() -> dict:
    return client_signal_engine.current()


@router.get("/latest")
async def get_latest_client_signal_engine_signals() -> dict:
    return client_signal_engine.latest()


@router.get("/diagnostics/{symbol}")
async def get_client_signal_engine_diagnostics(symbol: str) -> dict:
    signal = client_signal_engine.signal_for_symbol(symbol)
    return {
        "symbol": signal.get("symbol"),
        "signal": signal.get("signal"),
        "risk_status": signal.get("risk_status"),
        "execution_status": signal.get("execution_status"),
        "setup_reason": signal.get("setup_reason"),
        "approval_audit": signal.get("approval_audit"),
        "strategy_components": signal.get("strategy_components"),
        "quality_score": signal.get("quality_score"),
        "market_structure_state": signal.get("market_structure_state"),
        "candle_source": signal.get("candle_source"),
        "simulation_only": True,
        "live_execution_enabled": False,
        "broker_execution_enabled": False,
        "execution_allowed": False,
    }


@router.post("/refresh")
async def refresh_client_signal_engine() -> dict:
    return client_signal_engine.refresh()


@router.get("/history")
async def get_client_signal_engine_history(limit: int = 100) -> list[dict]:
    return client_signal_engine.history(limit)


@router.get("/history/{symbol}")
async def get_client_signal_engine_history_for_symbol(symbol: str, limit: int = 100) -> list[dict]:
    return client_signal_engine.history_for_symbol(symbol, limit)


@router.get("/EURUSD")
async def get_eurusd_signal() -> dict:
    return client_signal_engine.signal_for_symbol("EURUSD")


@router.get("/XAUUSD")
async def get_xauusd_signal() -> dict:
    return client_signal_engine.signal_for_symbol("XAUUSD")


@router.get("/NIFTY50")
async def get_nifty50_signal() -> dict:
    return client_signal_engine.signal_for_symbol("NIFTY50")
