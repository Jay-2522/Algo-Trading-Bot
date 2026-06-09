from datetime import datetime, timezone
from typing import Any

from backend.brokers.broker_account_models import (
    BrokerAccountConfig,
    BrokerAccountLayerStatus,
    BrokerAccountStatus,
    CurrentTerminalAccount,
)
from backend.mt5_demo.mt5_demo_service import MT5DemoService


class BrokerAccountService:
    """Read-only broker account registry for future multi-account support."""

    def __init__(self, mt5_demo_service: MT5DemoService | None = None) -> None:
        self.mt5_demo_service = mt5_demo_service or MT5DemoService()
        self._configs: dict[str, BrokerAccountConfig] = {}
        for config in [
            BrokerAccountConfig(broker_id="STARTRADER", broker_name="StarTrader"),
            BrokerAccountConfig(broker_id="FXPRO", broker_name="FxPro"),
            BrokerAccountConfig(broker_id="VANTAGE", broker_name="Vantage"),
        ]:
            self.register_account(config)

    def register_account(self, config: BrokerAccountConfig) -> BrokerAccountConfig:
        locked = config.model_copy(update={"execution_enabled": False})
        self._configs[locked.broker_id] = locked
        return locked

    def get_status(self) -> dict[str, Any]:
        layer = BrokerAccountLayerStatus(
            status="BROKER_ACCOUNT_FOUNDATION_READY",
            mode="BROKER_ACCOUNT_FOUNDATION_ONLY",
            supported_brokers=list(self._configs.keys()),
            accounts=self.list_accounts(),
            current_terminal_account=self.current_terminal_account(),
            timestamp=self._timestamp(),
        ).model_dump(mode="json")
        layer["account_layer"] = "FOUNDATION_ONLY"
        return layer

    def list_accounts(self) -> list[BrokerAccountStatus]:
        return [self.get_account_status(broker_id) for broker_id in self._configs]

    def get_account_status(self, broker_id: str) -> BrokerAccountStatus:
        normalized = str(broker_id or "").strip().upper()
        config = self._configs.get(normalized)
        if config is None:
            raise KeyError(normalized)
        connected = bool(config.account_login and config.server)
        return BrokerAccountStatus(
            broker_id=config.broker_id,
            broker_name=config.broker_name,
            platform=config.platform,
            account_login=config.account_login,
            server=config.server,
            account_type=config.account_type,
            connection_status="CONNECTED" if connected else "PENDING_CONNECTION",
            balance=None,
            equity=None,
            margin=None,
            free_margin=None,
            enabled=config.enabled,
            execution_enabled=False,
            last_sync=self._timestamp() if connected else None,
            message="Broker account connected for preview only." if connected else "Broker account not connected yet.",
        )

    def get_account_config(self, broker_id: str) -> BrokerAccountConfig:
        normalized = str(broker_id or "").strip().upper()
        config = self._configs.get(normalized)
        if config is None:
            raise KeyError(normalized)
        return config

    def sync_accounts(self) -> dict[str, Any]:
        return {
            "status": "SYNCED_READ_ONLY",
            "accounts": [account.model_dump(mode="json") for account in self.list_accounts()],
            "current_terminal_account": self.current_terminal_account().model_dump(mode="json"),
            "message": "StarTrader, FxPro, and Vantage are pending connection. Current MT5 terminal is shown separately.",
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }

    def readiness(self) -> dict[str, Any]:
        accounts = self.list_accounts()
        return {
            "status": "PENDING_BROKER_CONNECTIONS",
            "ready": False,
            "brokers_ready": 0,
            "brokers_total": len(accounts),
            "accounts": [account.model_dump(mode="json") for account in accounts],
            "current_terminal_account": self.current_terminal_account().model_dump(mode="json"),
            "blockers": [
                "StarTrader account not connected.",
                "FxPro account not connected.",
                "Vantage account not connected.",
                "Live and broker execution remain disabled.",
            ],
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "execution_allowed": False,
            "timestamp": self._timestamp(),
        }

    def current_terminal_account(self) -> CurrentTerminalAccount:
        account = self.mt5_demo_service.get_account()
        connected = bool(account.get("account_connected"))
        server = self._text(account.get("server"))
        login = self._text(account.get("login"))
        return CurrentTerminalAccount(
            connected=connected,
            account_login=login or None,
            server=server or None,
            account_type=self._text(account.get("account_type")) or None,
            balance=self._number(account.get("balance")),
            equity=self._number(account.get("equity")),
            margin=self._number(account.get("used_margin")),
            free_margin=self._number(account.get("free_margin")),
            currency=None,
            message="Current MT5 terminal account; not mapped to StarTrader, FxPro, or Vantage.",
        )

    def _number(self, value: Any) -> float | None:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str) and value.strip():
            try:
                return float(value)
            except ValueError:
                return None
        return None

    def _text(self, value: Any) -> str:
        return str(value or "").strip()

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()
