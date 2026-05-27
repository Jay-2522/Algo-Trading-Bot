from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SupportedBroker(BaseModel):
    broker_id: Literal["STARTRADER", "FXPRO", "VANTAGE"]
    display_name: str
    platform: Literal["MT5", "MT4_MT5", "UNKNOWN"]
    supported_account_modes: list[Literal["DEMO", "LIVE_DISABLED", "READ_ONLY"]] = Field(default_factory=list)
    supported_markets: list[str] = Field(default_factory=list)
    notes: str
    simulation_only: bool = True


class BrokerSymbolMapping(BaseModel):
    broker_id: str
    canonical_symbol: str
    broker_symbol: str | None = None
    supported: bool = False
    market_type: str
    notes: str


class BrokerCompatibilityResult(BaseModel):
    broker_id: str
    canonical_symbol: str
    broker_symbol: str | None = None
    supported: bool = False
    demo_ready: bool = False
    read_only_supported: bool = False
    live_execution_enabled: bool = False
    message: str


class BrokerDemoReadinessReport(BaseModel):
    broker_id: str
    ready_for_demo_testing: bool = False
    supported_symbols: list[str] = Field(default_factory=list)
    unsupported_symbols: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    safety_status: str = "SIMULATION_ONLY_LIVE_EXECUTION_DISABLED"
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)
