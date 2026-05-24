from datetime import datetime, timezone
from typing import List

from pydantic import BaseModel, Field


class RiskConfig(BaseModel):
    """Central policy limits used by risk controls."""

    max_risk_per_trade_percent: float
    max_daily_drawdown_percent: float
    max_consecutive_losses: int
    max_allowed_spread: float
    max_allowed_slippage: float
    trading_enabled: bool


class PositionSizeRequest(BaseModel):
    """Inputs for a read-only risk-based position size calculation."""

    account_balance: float
    risk_percent: float
    stop_loss_pips: float
    pip_value: float


class PositionSizeResponse(BaseModel):
    """Calculated exposure size; never an order instruction."""

    lot_size: float
    risk_amount: float
    stop_loss_pips: float
    status: str


class RiskCheckRequest(BaseModel):
    """Current risk conditions evaluated before future execution."""

    symbol: str = Field(..., min_length=1)
    account_balance: float
    current_drawdown_percent: float
    consecutive_losses: int
    current_spread: float
    expected_slippage: float


class RiskCheckResponse(BaseModel):
    """Permission result for a proposed future trading workflow."""

    allowed: bool
    reasons: List[str] = Field(default_factory=list)
    risk_level: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RiskStatus(BaseModel):
    """Current operational status of the risk engine."""

    trading_enabled: bool
    kill_switch_active: bool
    daily_drawdown_ok: bool
    consecutive_losses_ok: bool
    spread_ok: bool
    slippage_ok: bool
    overall_status: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class KillSwitchActivationRequest(BaseModel):
    """Manual reason supplied when halting future trading permission."""

    reason: str = Field(..., min_length=1)

