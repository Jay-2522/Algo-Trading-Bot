from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


ReportType = Literal["DAILY", "WEEKLY", "SYMBOL", "RISK", "TRADE_JOURNAL", "EXECUTION_HISTORY"]


class ClientReport(BaseModel):
    report_id: str = Field(default_factory=lambda: f"client_report_{uuid4().hex[:12]}")
    report_type: ReportType
    period: str
    generated_at: datetime = Field(default_factory=utc_now)
    summary: dict[str, Any] = Field(default_factory=dict)
    symbol_performance: list[dict[str, Any]] = Field(default_factory=list)
    session_performance: list[dict[str, Any]] = Field(default_factory=list)
    risk_summary: dict[str, Any] = Field(default_factory=dict)
    trade_journal_summary: dict[str, Any] = Field(default_factory=dict)
    execution_summary: dict[str, Any] = Field(default_factory=dict)
    simulation_only: bool = True
    demo_execution: bool = True
    live_execution_enabled: bool = False
    broker_execution_enabled: bool = False

    def model_post_init(self, __context: Any) -> None:
        self.simulation_only = True
        self.demo_execution = True
        self.live_execution_enabled = False
        self.broker_execution_enabled = False
