from typing import List

from pydantic import BaseModel, Field


class MT5ConnectionStatus(BaseModel):
    connected: bool
    initialized: bool
    terminal_available: bool
    message: str
    timestamp: str


class MT5AccountInfo(BaseModel):
    login: int | None = None
    server: str | None = None
    balance: float | None = None
    equity: float | None = None
    margin: float | None = None
    free_margin: float | None = None
    currency: str | None = None
    leverage: int | None = None
    company: str | None = None


class MT5SymbolInfo(BaseModel):
    symbol: str
    visible: bool | None = None
    trade_allowed: bool | None = None
    point: float | None = None
    digits: int | None = None
    spread: float | None = None
    volume_min: float | None = None
    volume_max: float | None = None
    volume_step: float | None = None


class MT5TickInfo(BaseModel):
    symbol: str
    bid: float | None = None
    ask: float | None = None
    last: float | None = None
    volume: float | None = None
    time: str | None = None


class MT5PositionInfo(BaseModel):
    ticket: int | None = None
    symbol: str | None = None
    type: str | None = None
    volume: float | None = None
    price_open: float | None = None
    profit: float | None = None
    sl: float | None = None
    tp: float | None = None


class MT5HealthStatus(BaseModel):
    connection: MT5ConnectionStatus
    account_available: bool
    terminal_info_available: bool
    symbols_checked: List[str] = Field(default_factory=list)
    overall_status: str
    timestamp: str

