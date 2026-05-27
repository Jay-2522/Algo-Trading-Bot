from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MT5TerminalReadiness(BaseModel):
    terminal_available: bool = False
    initialized: bool = False
    read_only_mode: bool = True
    account_available: bool = False
    broker_server: str | None = None
    message: str
    simulation_only: bool = True
    live_execution_enabled: bool = False


class BrokerSymbolVerification(BaseModel):
    broker_id: str
    canonical_symbol: str
    expected_broker_symbol: str | None = None
    mt5_symbol_found: bool = False
    visible: bool | None = None
    trade_allowed: bool | None = None
    digits: int | None = None
    point: float | None = None
    spread: int | float | None = None
    verification_status: Literal["VERIFIED", "NOT_FOUND", "CONDITIONAL", "MT5_UNAVAILABLE", "UNSUPPORTED"]
    message: str


class BrokerDemoVerificationReport(BaseModel):
    broker_id: str
    terminal_readiness: MT5TerminalReadiness
    symbol_verifications: list[BrokerSymbolVerification] = Field(default_factory=list)
    verified_symbols: list[str] = Field(default_factory=list)
    missing_symbols: list[str] = Field(default_factory=list)
    conditional_symbols: list[str] = Field(default_factory=list)
    ready_for_demo_observation: bool = False
    ready_for_demo_execution: bool = False
    safety_status: str = "READ_ONLY_SIMULATION_ONLY_LIVE_EXECUTION_DISABLED"
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)
