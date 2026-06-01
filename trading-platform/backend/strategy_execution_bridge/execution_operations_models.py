from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


PipelineStage = Literal[
    "STRATEGY_SIGNAL",
    "BRIDGE",
    "RISK",
    "QUEUE_PREVIEW",
    "APPROVAL",
    "DEMO_CANDIDATE",
    "FINAL_EXECUTION",
    "MT5_DEMO_RESULT",
    "TRADE_COPIER",
    "CONFIRMATION",
]


class ExecutionOperationsOverview(BaseModel):
    status: str = "OPERATIONAL"
    pipeline_ready: bool = True
    bridge_ready: bool = True
    queue_preview_ready: bool = True
    approval_ready: bool = True
    final_execution_ready: bool = True
    copier_ready: bool = True
    confirmation_ready: bool = True
    total_bridge_decisions: int = 0
    total_queue_previews: int = 0
    total_approvals: int = 0
    total_candidates: int = 0
    total_final_executions: int = 0
    total_copy_results: int = 0
    blocked_count: int = 0
    rejected_count: int = 0
    demo_execution_count: int = 0
    health_score: int = 100
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


class ExecutionPipelineEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"exec_pipeline_event_{uuid4().hex[:12]}")
    stage: PipelineStage
    status: str
    entity_id: str | None = None
    symbol: str | None = None
    action: str | None = None
    message: str
    severity: Literal["INFO", "WARNING", "ERROR"] = "INFO"
    timestamp: datetime = Field(default_factory=utc_now)
