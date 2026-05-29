from datetime import datetime, timezone

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ExecutionDashboardOverview(BaseModel):
    execution_bridge_status: str
    routing_status: str
    copier_status: str
    confirmation_status: str
    reconciliation_status: str
    risk_status: str
    health_score: int
    execution_readiness: str
    simulation_only: bool = True
    live_execution_enabled: bool = False
    broker_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)


class ExecutionDashboardCard(BaseModel):
    title: str
    value: str
    status: str
    description: str


class ExecutionDashboardSummary(BaseModel):
    total_demo_executions: int
    total_confirmations: int
    total_reconciliations: int
    total_risk_decisions: int
    total_copy_batches: int
    total_multi_account_batches: int
    blocked_attempts: int
    warnings: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)

