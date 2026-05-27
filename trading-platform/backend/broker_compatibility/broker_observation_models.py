from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class BrokerSymbolSnapshot(BaseModel):
    broker_id: str
    canonical_symbol: str
    broker_symbol: str | None = None
    bid: float | None = None
    ask: float | None = None
    spread: float | None = None
    digits: int | None = None
    point: float | None = None
    timestamp: datetime = Field(default_factory=utc_now)
    source: Literal["MT5_READ_ONLY", "SIMULATION_FALLBACK", "UNAVAILABLE"]
    available: bool = False
    message: str


class BrokerObservationReport(BaseModel):
    broker_id: str
    observation_mode: Literal["READ_ONLY", "SIMULATION_FALLBACK", "UNAVAILABLE"]
    symbols_observed: list[str] = Field(default_factory=list)
    snapshots: list[BrokerSymbolSnapshot] = Field(default_factory=list)
    unavailable_symbols: list[str] = Field(default_factory=list)
    observation_status: Literal["OPERATIONAL", "PARTIAL", "UNAVAILABLE"]
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)


class BrokerObservationStatus(BaseModel):
    status: Literal["OPERATIONAL", "DEGRADED", "UNAVAILABLE"] = "OPERATIONAL"
    read_only_mode: bool = True
    supported_brokers: list[str] = Field(default_factory=list)
    supported_symbols: list[str] = Field(default_factory=list)
    simulation_only: bool = True
    live_execution_enabled: bool = False
    message: str
