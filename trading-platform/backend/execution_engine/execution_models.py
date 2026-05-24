from typing import Any, Dict, List

from pydantic import BaseModel, Field


class OrderRequest(BaseModel):
    """Proposed order inputs accepted for validation and simulation only."""

    symbol: str
    side: str
    order_type: str
    lot_size: float
    entry_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    comment: str | None = None


class OrderValidationResult(BaseModel):
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class ExecutionResult(BaseModel):
    success: bool
    execution_id: str
    symbol: str
    side: str
    lot_size: float
    execution_mode: str
    status: str
    message: str
    timestamp: str


class ExecutionStatus(BaseModel):
    execution_id: str
    status: str
    symbol: str
    side: str
    created_at: str
    updated_at: str


class ExecutionLog(BaseModel):
    execution_id: str
    event_type: str
    message: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str

