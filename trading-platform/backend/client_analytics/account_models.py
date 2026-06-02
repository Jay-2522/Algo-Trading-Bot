from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


AccountType = Literal["MASTER", "COPIER"]
SyncStatus = Literal["SYNCHRONIZED", "DEGRADED", "PENDING", "UNKNOWN"]


class AccountAnalyticsSummary(BaseModel):
    account_id: str
    account_name: str
    account_type: AccountType
    total_signals: int = 0
    total_executions: int = 0
    total_copied_trades: int = 0
    win_rate: float = 0.0
    net_pnl: float = 0.0
    max_drawdown: float = 0.0
    synchronization_status: SyncStatus = "UNKNOWN"
    last_sync_time: datetime | None = None
    simulation_only: bool = True
    demo_execution: bool = True
    live_execution_enabled: bool = False
    broker_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)

    def model_post_init(self, __context: Any) -> None:
        self.simulation_only = True
        self.demo_execution = True
        self.live_execution_enabled = False
        self.broker_execution_enabled = False
