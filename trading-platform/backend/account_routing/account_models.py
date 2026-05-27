from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class BrokerAccountProfile(BaseModel):
    account_id: str
    broker_id: str
    display_name: str
    account_mode: Literal["DEMO", "READ_ONLY", "LIVE_DISABLED"] = "DEMO"
    supported_symbols: list[str] = Field(default_factory=list)
    account_group: str
    enabled: bool = True
    read_only: bool = True
    demo_ready: bool = False
    live_execution_enabled: bool = False
    notes: str = ""


class AccountRoutingPolicy(BaseModel):
    policy_id: str = "default_copy_to_all_demo_read_only"
    routing_mode: Literal["COPY_TO_ALL", "PRIMARY_ONLY", "BROKER_SPECIFIC", "SYMBOL_SPECIFIC", "DISABLED"] = "COPY_TO_ALL"
    enabled_brokers: list[str] = Field(default_factory=lambda: ["STARTRADER", "FXPRO", "VANTAGE"])
    enabled_symbols: list[str] = Field(default_factory=lambda: ["EURUSD", "XAUUSD", "NIFTY50"])
    max_accounts_per_signal: int = 3
    require_demo_ready: bool = True
    require_read_only_verified: bool = True
    live_execution_enabled: bool = False


class RejectedAccountReason(BaseModel):
    account_id: str
    broker_id: str
    reason: str


class AccountRoutingDecision(BaseModel):
    decision_id: str = Field(default_factory=lambda: f"acct_route_{uuid4().hex[:12]}")
    signal_id: str
    canonical_symbol: str
    action: str
    routing_mode: str
    eligible_accounts: list[BrokerAccountProfile] = Field(default_factory=list)
    rejected_accounts: list[RejectedAccountReason] = Field(default_factory=list)
    routing_ready: bool = False
    rejection_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)
