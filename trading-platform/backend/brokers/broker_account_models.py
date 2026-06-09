from typing import Literal

from pydantic import BaseModel, Field


BrokerId = Literal["STARTRADER", "FXPRO", "VANTAGE"]
AccountType = Literal["DEMO", "LIVE"]
Platform = Literal["MT5"]


class BrokerAccountConfig(BaseModel):
    broker_id: BrokerId
    broker_name: str
    platform: Platform = "MT5"
    account_login: str | None = None
    server: str | None = None
    account_type: AccountType | None = None
    enabled: bool = True
    execution_enabled: bool = False
    max_open_trades: int = 1
    open_positions: list[dict] = Field(default_factory=list)


class BrokerAccountStatus(BaseModel):
    broker_id: BrokerId
    broker_name: str
    platform: Platform = "MT5"
    account_login: str | None = None
    server: str | None = None
    account_type: AccountType | None = None
    connection_status: str
    balance: float | None = None
    equity: float | None = None
    margin: float | None = None
    free_margin: float | None = None
    currency: str | None = None
    enabled: bool = True
    execution_enabled: bool = False
    last_sync: str | None = None
    message: str
    live_execution_enabled: bool = False
    broker_execution_enabled: bool = False


class CurrentTerminalAccount(BaseModel):
    connected: bool
    platform: Platform = "MT5"
    account_login: str | None = None
    server: str | None = None
    account_type: AccountType | str | None = None
    balance: float | None = None
    equity: float | None = None
    margin: float | None = None
    free_margin: float | None = None
    currency: str | None = None
    label: str = "Current Test Terminal"
    message: str
    live_execution_enabled: bool = False
    broker_execution_enabled: bool = False


class BrokerAccountLayerStatus(BaseModel):
    status: str
    mode: str
    supported_brokers: list[str]
    accounts: list[BrokerAccountStatus]
    current_terminal_account: CurrentTerminalAccount
    simulation_only: bool = True
    live_execution_enabled: bool = False
    broker_execution_enabled: bool = False
    execution_allowed: bool = False
    timestamp: str
