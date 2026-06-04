from backend.nifty50.indian_broker_registry import IndianBrokerRegistry
from backend.nifty50.nifty_models import NIFTY50ReadinessStatus


class NIFTYReadinessService:
    def __init__(self, broker_registry: IndianBrokerRegistry | None = None) -> None:
        self.broker_registry = broker_registry or IndianBrokerRegistry()

    def get_blockers(self) -> list[str]:
        return [
            "Indian broker not selected",
            "Execution not implemented",
            "Execution bridge missing",
            "Broker integration missing",
            "Analytics integration pending",
        ]

    def get_warnings(self) -> list[str]:
        return [
            "No broker API credentials should be configured in this phase.",
            "Market data ingestion is manual-only; no live broker feed is connected.",
            "Broker execution remains disabled.",
        ]

    def get_status(self) -> NIFTY50ReadinessStatus:
        return NIFTY50ReadinessStatus(
            status="RISK_QUALIFICATION_READY",
            broker_architecture_ready=True,
            market_data_ready=True,
            strategy_ready=True,
            risk_ready=True,
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
            "Use manual candle/tick ingestion to validate NIFTY50 strategy context.",
            "Add NIFTY50 analytics integration.",
            "Add paper/demo execution validation only after explicit execution-layer approval.",
        ]
