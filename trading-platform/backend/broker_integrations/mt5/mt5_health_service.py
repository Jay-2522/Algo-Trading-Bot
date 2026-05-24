from datetime import datetime, timezone

from backend.broker_integrations.mt5.mt5_account_service import MT5AccountService
from backend.broker_integrations.mt5.mt5_connection_manager import MT5ConnectionManager
from backend.broker_integrations.mt5.mt5_data_models import MT5HealthStatus
from backend.broker_integrations.mt5.mt5_symbol_service import MT5SymbolService


class MT5HealthService:
    """Monitor read-only terminal, account, and symbol-data availability."""

    def __init__(self, connection_manager: MT5ConnectionManager | None = None) -> None:
        self.connection_manager = connection_manager or MT5ConnectionManager()
        self.account_service = MT5AccountService(self.connection_manager)
        self.symbol_service = MT5SymbolService(self.connection_manager)

    def get_health_status(self, symbols_to_check: list[str] | None = None) -> MT5HealthStatus:
        symbols = symbols_to_check or ["XAUUSD"]
        connection = self.connection_manager.get_connection_status()
        if not connection.connected:
            return MT5HealthStatus(
                connection=connection,
                account_available=False,
                terminal_info_available=False,
                symbols_checked=[],
                overall_status="UNAVAILABLE",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        account = self.account_service.get_account_info()
        account_available = account.login is not None
        terminal_info_available = self._terminal_info_available()
        checked_symbols = [
            symbol.strip().upper()
            for symbol in symbols
            if self.symbol_service.ensure_symbol_visible(symbol).visible is not None
        ]
        operational = account_available and terminal_info_available and len(checked_symbols) == len(symbols)
        return MT5HealthStatus(
            connection=connection,
            account_available=account_available,
            terminal_info_available=terminal_info_available,
            symbols_checked=checked_symbols,
            overall_status="OPERATIONAL" if operational else "DEGRADED",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def _terminal_info_available(self) -> bool:
        try:
            return self.connection_manager.mt5.terminal_info() is not None
        except Exception:
            return False
