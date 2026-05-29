from datetime import datetime, timezone

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DeliveryReadiness(BaseModel):
    overall_score: int
    dashboard_ready: bool
    orchestration_ready: bool
    monitoring_ready: bool
    broker_ready: bool
    portfolio_ready: bool
    control_center_ready: bool
    simulation_ready: bool
    deployment_ready: bool
    client_demo_ready: bool
    remaining_items: list[str] = Field(default_factory=list)
    simulation_only: bool = True
    live_execution_enabled: bool = False
    timestamp: datetime = Field(default_factory=utc_now)
