from backend.broker_integrations.mt5.mt5_connection_manager import MT5ConnectionManager
from backend.broker_integrations.mt5.mt5_data_models import MT5AccountInfo


class MT5AccountService:
    """Read account data from MT5 without altering account state."""

    def __init__(self, connection_manager: MT5ConnectionManager) -> None:
        self.connection_manager = connection_manager

    def get_account_info(self) -> MT5AccountInfo:
        if not self.connection_manager.is_initialized():
            return MT5AccountInfo()

        try:
            account = self.connection_manager.mt5.account_info()
            if account is None:
                return MT5AccountInfo()
            return MT5AccountInfo(
                login=getattr(account, "login", None),
                server=getattr(account, "server", None),
                balance=getattr(account, "balance", None),
                equity=getattr(account, "equity", None),
                margin=getattr(account, "margin", None),
                free_margin=getattr(account, "margin_free", None),
                currency=getattr(account, "currency", None),
                leverage=getattr(account, "leverage", None),
                company=getattr(account, "company", None),
            )
        except Exception:
            return MT5AccountInfo()
