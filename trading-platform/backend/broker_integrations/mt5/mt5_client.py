from typing import Any, Optional

from backend.config.settings import get_settings
from backend.utils.logger import get_logger


logger = get_logger(__name__)

MT5_IMPORT_ERROR: Optional[Exception] = None

try:
    import MetaTrader5 as mt5
except Exception as exc:  # pragma: no cover - depends on local trading terminal setup
    mt5 = None
    MT5_IMPORT_ERROR = exc


class MT5Client:
    """Safe MetaTrader 5 connection client.

    This Day 1 client intentionally exposes read-only account and market data
    methods. Order placement will be added later behind execution, risk, audit,
    and broker-abstraction controls.
    """

    def __init__(
        self,
        login: Optional[int] = None,
        server: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        settings = get_settings()
        self.login = login or settings.mt5_login
        self.server = server or settings.mt5_server
        self.password = password or settings.mt5_password
        self.connected = False

    def connect(self) -> bool:
        if mt5 is None:
            raise RuntimeError(
                "MetaTrader5 package is unavailable. Run pip install -r requirements.txt "
                "and confirm NumPy is pinned to a MetaTrader5-compatible version."
            ) from MT5_IMPORT_ERROR

        try:
            initialized = mt5.initialize()
            if not initialized:
                raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")

            if self.login and self.server and self.password:
                authorized = mt5.login(
                    login=int(self.login),
                    password=self.password,
                    server=self.server,
                )
                if not authorized:
                    raise RuntimeError(f"MT5 login failed: {mt5.last_error()}")

            self.connected = True
            logger.info("MT5 connection initialized")
            return True
        except Exception:
            self.connected = False
            logger.exception("MT5 connection failed")
            raise

    def disconnect(self) -> None:
        if mt5 is not None:
            mt5.shutdown()
        self.connected = False
        logger.info("MT5 connection closed")

    def get_account_info(self) -> Any:
        self._ensure_connected()
        account_info = mt5.account_info()
        if account_info is None:
            raise RuntimeError(f"Unable to fetch MT5 account info: {mt5.last_error()}")
        return account_info

    def get_symbol_info(self, symbol: str) -> Any:
        self._ensure_connected()
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            raise RuntimeError(f"Unable to fetch symbol info for {symbol}: {mt5.last_error()}")
        return symbol_info

    def get_latest_tick(self, symbol: str) -> Any:
        self._ensure_connected()
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise RuntimeError(f"Unable to fetch latest tick for {symbol}: {mt5.last_error()}")
        return tick

    def _ensure_connected(self) -> None:
        if mt5 is None:
            raise RuntimeError(
                "MetaTrader5 package is unavailable. Run pip install -r requirements.txt "
                "and confirm NumPy is pinned to a MetaTrader5-compatible version."
            ) from MT5_IMPORT_ERROR
        if not self.connected:
            raise RuntimeError("MT5 client is not connected. Call connect() first.")
