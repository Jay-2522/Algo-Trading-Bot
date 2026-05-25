from backend.market_data.validators import validate_symbol_name, validate_timeframe
from backend.orchestration.orchestration_models import SymbolMonitorConfig


class SymbolMonitor:
    """Maintain an in-memory monitored-symbol list without starting a loop."""

    def __init__(self, config: SymbolMonitorConfig | None = None) -> None:
        self._config = config or SymbolMonitorConfig()

    def get_symbols(self) -> list[str]:
        return list(self._config.symbols)

    def add_symbol(self, symbol: str) -> list[str]:
        normalized_symbol = validate_symbol_name(symbol)
        if normalized_symbol not in self._config.symbols:
            self._config.symbols.append(normalized_symbol)
        return self.get_symbols()

    def remove_symbol(self, symbol: str) -> list[str]:
        normalized_symbol = validate_symbol_name(symbol)
        if normalized_symbol in self._config.symbols:
            self._config.symbols.remove(normalized_symbol)
        return self.get_symbols()

    def get_config(self) -> SymbolMonitorConfig:
        self._config.default_timeframe = validate_timeframe(self._config.default_timeframe)
        return self._config.model_copy(deep=True)
