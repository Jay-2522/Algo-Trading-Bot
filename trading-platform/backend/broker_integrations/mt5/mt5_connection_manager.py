from datetime import datetime, timezone
from typing import Any

from backend.broker_integrations.mt5.mt5_data_models import MT5ConnectionStatus


try:
    import MetaTrader5 as imported_mt5
except Exception:  # pragma: no cover - depends on local MT5 installation
    imported_mt5 = None


_DEFAULT_MODULE = object()


class MT5ConnectionManager:
    """Safely manages a read-only MetaTrader 5 terminal connection lifecycle."""

    def __init__(self, mt5_module: Any = _DEFAULT_MODULE) -> None:
        self.mt5 = imported_mt5 if mt5_module is _DEFAULT_MODULE else mt5_module
        self._initialized = False
        self._message = "MT5 connection has not been initialized."

    def initialize(self) -> MT5ConnectionStatus:
        if self.mt5 is None:
            self._message = "MetaTrader5 package or terminal is unavailable."
            return self.get_connection_status()

        try:
            if self.mt5.initialize():
                self._initialized = True
                self._message = "MT5 initialized for read-only broker data access."
            else:
                self._initialized = False
                self._message = f"MT5 initialization failed: {self.mt5.last_error()}"
        except Exception as exc:
            self._initialized = False
            self._message = f"MT5 initialization failed safely: {exc}"
        return self.get_connection_status()

    def shutdown(self) -> MT5ConnectionStatus:
        if self.mt5 is not None and self._initialized:
            try:
                self.mt5.shutdown()
            except Exception:
                pass
        self._initialized = False
        self._message = "MT5 connection is shut down."
        return self.get_connection_status()

    def is_initialized(self) -> bool:
        return self._initialized

    def get_connection_status(self) -> MT5ConnectionStatus:
        return MT5ConnectionStatus(
            connected=self._initialized,
            initialized=self._initialized,
            terminal_available=self._initialized,
            message=self._message,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

