from backend.broker_integrations.mt5.mt5_connection_manager import MT5ConnectionManager
from backend.broker_integrations.mt5.mt5_data_models import MT5PositionInfo


class MT5PositionService:
    """Read open MT5 positions without changing or closing them."""

    def __init__(self, connection_manager: MT5ConnectionManager) -> None:
        self.connection_manager = connection_manager

    def get_open_positions(self) -> list[MT5PositionInfo]:
        return self._read_positions()

    def get_positions_by_symbol(self, symbol: str) -> list[MT5PositionInfo]:
        normalized_symbol = symbol.strip().upper() if symbol else ""
        if not normalized_symbol:
            raise ValueError("Symbol cannot be empty.")
        return self._read_positions(symbol=normalized_symbol)

    def _read_positions(self, symbol: str | None = None) -> list[MT5PositionInfo]:
        if not self.connection_manager.is_initialized():
            return []
        try:
            positions = (
                self.connection_manager.mt5.positions_get(symbol=symbol)
                if symbol
                else self.connection_manager.mt5.positions_get()
            )
            if positions is None:
                return []
            return [self._to_model(position) for position in positions]
        except Exception:
            return []

    def _to_model(self, position) -> MT5PositionInfo:
        type_code = getattr(position, "type", None)
        type_name = {0: "BUY", 1: "SELL"}.get(type_code, str(type_code) if type_code is not None else None)
        return MT5PositionInfo(
            ticket=getattr(position, "ticket", None),
            symbol=getattr(position, "symbol", None),
            type=type_name,
            volume=getattr(position, "volume", None),
            price_open=getattr(position, "price_open", None),
            profit=getattr(position, "profit", None),
            sl=getattr(position, "sl", None),
            tp=getattr(position, "tp", None),
        )
