from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class DemoOrderDryRunRequest:
    symbol: str
    action: str
    lot: float
    entry_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    risk_decision_id: str | None = None
    gate_decision_id: str | None = None
    manual_confirmation: bool = False


@dataclass
class DemoOrderDryRunResult:
    dry_run_id: str
    symbol: str
    action: str
    lot: float
    entry_price: float | None
    stop_loss: float | None
    take_profit: float | None
    validation_passed: bool
    rejection_reasons: list[str] = field(default_factory=list)
    order_payload_preview: dict[str, Any] = field(default_factory=dict)
    would_send_to_mt5: bool = False
    mt5_order_sent: bool = False
    execution_allowed: bool = False
    simulation_only: bool = True
    live_execution_enabled: bool = False
    broker_execution_enabled: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
