from backend.broker_compatibility.broker_compatibility_service import BrokerCompatibilityService


class BrokerMonitor:
    """Summarize broker compatibility and read-only feed readiness."""

    def __init__(self, broker_service: BrokerCompatibilityService | None = None) -> None:
        self.broker_service = broker_service or BrokerCompatibilityService()

    def get_broker_health(self) -> dict:
        brokers = self.broker_service.list_brokers()
        feed_status = self.broker_service.get_feed_quality_status()
        observation_status = self.broker_service.get_observation_status()
        return {
            "brokers": [broker.broker_id for broker in brokers],
            "broker_count": len(brokers),
            "observation_status": getattr(observation_status, "status", "UNKNOWN"),
            "feed_quality_status": feed_status.get("status", "UNKNOWN"),
            "tracked_brokers": ["STARTRADER", "FXPRO", "VANTAGE"],
            "simulation_only": True,
            "live_execution_enabled": False,
        }
