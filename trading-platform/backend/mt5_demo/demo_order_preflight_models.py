from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class DemoOrderPreflightRequest:
    symbol: str
    action: str
    lot: float
    entry_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    dry_run_id: str | None = None


@dataclass
class DemoOrderPreflightResult:
    preflight_id: str
    dry_run_id: str | None
    validation_passed: bool
    symbol_check: bool
    action_check: bool
    lot_check: bool
    stop_loss_check: bool
    take_profit_check: bool
    risk_check: bool
    authorization_check: bool
    execution_gate_check: bool
    spread_check: bool
    market_data_check: bool
    warnings: list[str] = field(default_factory=list)
    rejection_reasons: list[str] = field(default_factory=list)
    would_be_allowed_in_demo: bool = False
    execution_allowed: bool = False
    simulation_only: bool = True
    live_execution_enabled: bool = False
    broker_execution_enabled: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
