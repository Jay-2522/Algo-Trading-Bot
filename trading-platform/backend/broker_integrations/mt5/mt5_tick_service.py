from datetime import datetime, timezone

from backend.broker_integrations.mt5.mt5_connection_manager import MT5ConnectionManager
from backend.broker_integrations.mt5.mt5_data_models import MT5TickInfo
from backend.broker_integrations.mt5.mt5_symbol_service import MT5SymbolService


class MT5TickService:
    """Read the latest available MT5 tick in a JSON-safe model."""

    def __init__(self, connection_manager: MT5ConnectionManager) -> None:
        self.connection_manager = connection_manager
        self.symbol_service = MT5SymbolService(connection_manager)

    def get_latest_tick(self, symbol: str) -> MT5TickInfo:
        symbol_info = self.symbol_service.ensure_symbol_visible(symbol)
        if not self.connection_manager.is_initialized():
            return MT5TickInfo(symbol=symbol_info.symbol)

        try:
            tick = self.connection_manager.mt5.symbol_info_tick(symbol_info.symbol)
            if tick is None:
                return MT5TickInfo(symbol=symbol_info.symbol)
            tick_time = getattr(tick, "time", None)
            return MT5TickInfo(
                symbol=symbol_info.symbol,
                bid=getattr(tick, "bid", None),
                ask=getattr(tick, "ask", None),
                last=getattr(tick, "last", None),
                volume=getattr(tick, "volume", None),
                time=(
                    datetime.fromtimestamp(tick_time, tz=timezone.utc).isoformat()
                    if tick_time is not None
                    else None
                ),
            )
        except Exception:
            return MT5TickInfo(symbol=symbol_info.symbol)

