from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class DemoExecutionSimulationRequest:
    symbol: str
    action: str
    lot: float
    entry_price: float
    stop_loss: float
    take_profit: float
    preflight_id: str | None = None


@dataclass
class DemoExecutionSimulationResult:
    simulation_id: str
    preflight_id: str | None
    symbol: str
    action: str
    lot: float
    entry_price: float | None
    stop_loss: float | None
    take_profit: float | None
    simulated_risk_amount: float | None
    simulated_reward_amount: float | None
    risk_reward_ratio: float | None
    estimated_margin: float | None
    simulated_order_payload: dict[str, Any] = field(default_factory=dict)
    simulation_passed: bool = False
    execution_allowed: bool = False
    would_send_to_mt5: bool = False
    mt5_order_sent: bool = False
    simulation_only: bool = True
    live_execution_enabled: bool = False
    broker_execution_enabled: bool = False
    warnings: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
