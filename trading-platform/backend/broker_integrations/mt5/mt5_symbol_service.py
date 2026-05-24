from backend.broker_integrations.mt5.mt5_connection_manager import MT5ConnectionManager
from backend.broker_integrations.mt5.mt5_data_models import MT5SymbolInfo


class MT5SymbolService:
    """Read symbol metadata and safely make symbols visible for data access."""

    def __init__(self, connection_manager: MT5ConnectionManager) -> None:
        self.connection_manager = connection_manager

    def get_symbol_info(self, symbol: str) -> MT5SymbolInfo:
        normalized_symbol = self._normalize_symbol(symbol)
        if not self._ready():
            return MT5SymbolInfo(symbol=normalized_symbol)

        try:
            raw_symbol = self.connection_manager.mt5.symbol_info(normalized_symbol)
            if raw_symbol is None:
                return MT5SymbolInfo(symbol=normalized_symbol)
            trade_mode = getattr(raw_symbol, "trade_mode", None)
            disabled_mode = getattr(self.connection_manager.mt5, "SYMBOL_TRADE_MODE_DISABLED", None)
            trade_allowed = None if trade_mode is None else trade_mode != disabled_mode
            return MT5SymbolInfo(
                symbol=normalized_symbol,
                visible=getattr(raw_symbol, "visible", None),
                trade_allowed=trade_allowed,
                point=getattr(raw_symbol, "point", None),
                digits=getattr(raw_symbol, "digits", None),
                spread=getattr(raw_symbol, "spread", None),
                volume_min=getattr(raw_symbol, "volume_min", None),
                volume_max=getattr(raw_symbol, "volume_max", None),
                volume_step=getattr(raw_symbol, "volume_step", None),
            )
        except Exception:
            return MT5SymbolInfo(symbol=normalized_symbol)

    def ensure_symbol_visible(self, symbol: str) -> MT5SymbolInfo:
        normalized_symbol = self._normalize_symbol(symbol)
        symbol_info = self.get_symbol_info(normalized_symbol)
        if symbol_info.visible is False and self._ready():
            try:
                self.connection_manager.mt5.symbol_select(normalized_symbol, True)
                return self.get_symbol_info(normalized_symbol)
            except Exception:
                return symbol_info
        return symbol_info

    def _ready(self) -> bool:
        return self.connection_manager.is_initialized()

    def _normalize_symbol(self, symbol: str) -> str:
        normalized = symbol.strip().upper() if symbol else ""
        if not normalized:
            raise ValueError("Symbol cannot be empty.")
        return normalized
