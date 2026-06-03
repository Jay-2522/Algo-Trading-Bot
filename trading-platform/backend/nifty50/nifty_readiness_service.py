from backend.nifty50.indian_broker_registry import IndianBrokerRegistry
from backend.nifty50.nifty_models import NIFTY50ReadinessStatus


class NIFTYReadinessService:
    def __init__(self, broker_registry: IndianBrokerRegistry | None = None) -> None:
        self.broker_registry = broker_registry or IndianBrokerRegistry()

    def get_blockers(self) -> list[str]:
        return [
            "Indian broker not selected",
            "Live/paper market data not connected",
            "Execution not implemented",
            "NIFTY strategy layer not implemented",
        ]

    def get_warnings(self) -> list[str]:
        return [
            "No broker API credentials should be configured in this phase.",
            "Market data snapshot is placeholder-only and contains no fake NIFTY price.",
            "Broker execution remains disabled.",
        ]

    def get_status(self) -> NIFTY50ReadinessStatus:
        return NIFTY50ReadinessStatus(
            status="PENDING_BROKER_SELECTION",
            broker_architecture_ready=True,
            market_data_ready=False,
            strategy_ready=False,
            execution_ready=False,
            analytics_ready=True,
            selected_broker=None,
            recommended_broker="Dhan or Angel One",
            blockers=self.get_blockers(),
            warnings=self.get_warnings(),
        )

    def get_next_steps(self) -> list[str]:
        return [
            "Select Dhan, Angel One, or another supported broker candidate.",
            "Add sandbox/manual market data ingestion.",
            "Build NIFTY50 strategy layer.",
            "Add paper/demo execution validation after strategy readiness.",
        ]
