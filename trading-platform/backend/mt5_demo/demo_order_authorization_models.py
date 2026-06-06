from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


@dataclass
class DemoOrderAuthorizationStatus:
    environment: str = "DEMO"
    demo_order_testing_enabled: bool = False
    live_execution_enabled: bool = False
    broker_execution_enabled: bool = False
    execution_allowed: bool = False
    max_demo_lot: float = 0.01
    allowed_symbols: list[str] = field(default_factory=lambda: ["EURUSD", "XAUUSD"])
    authorization_required: bool = True
    risk_qualification_required: bool = True
    execution_gate_required: bool = True
    manual_confirmation_required: bool = True
    status: str = "LOCKED"
    warnings: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return asdict(self)
