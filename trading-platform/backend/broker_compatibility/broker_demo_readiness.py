from backend.broker_compatibility.broker_capability_checker import BrokerCapabilityChecker
from backend.broker_compatibility.broker_models import BrokerDemoReadinessReport
from backend.broker_compatibility.broker_registry import BrokerRegistry


class BrokerDemoReadinessChecker:
    """Demo-readiness checklist for broker compatibility research."""

    def __init__(
        self,
        registry: BrokerRegistry | None = None,
        capability_checker: BrokerCapabilityChecker | None = None,
    ) -> None:
        self.registry = registry or BrokerRegistry()
        self.capability_checker = capability_checker or BrokerCapabilityChecker(self.registry)

    def check_demo_readiness(self, broker_id: str) -> BrokerDemoReadinessReport:
        broker = self.registry.get_broker(broker_id)
        normalized = str(broker_id or "").strip().upper()
        if broker is None:
            return BrokerDemoReadinessReport(
                broker_id=normalized,
                ready_for_demo_testing=False,
                supported_symbols=[],
                unsupported_symbols=["EURUSD", "XAUUSD", "NIFTY50"],
                missing_requirements=["Broker is not registered."],
                simulation_only=True,
                live_execution_enabled=False,
            )

        results = self.capability_checker.check_all_client_symbols(broker.broker_id)
        supported = [result.canonical_symbol for result in results if result.supported]
        unsupported = [result.canonical_symbol for result in results if not result.supported]
        missing = [
            "Confirm broker-specific EURUSD/XAUUSD symbol names in demo terminal.",
            "Confirm read-only MT5/MT4-MT5 data connection before integration.",
            "Keep live execution disabled.",
        ]
        if "NIFTY50" in unsupported:
            missing.append("Verify whether NIFTY50 exists on this broker; currently treated as conditional/unsupported.")

        return BrokerDemoReadinessReport(
            broker_id=broker.broker_id,
            ready_for_demo_testing=bool(supported) and broker.platform in {"MT5", "MT4_MT5"},
            supported_symbols=supported,
            unsupported_symbols=unsupported,
            missing_requirements=missing,
            safety_status="SIMULATION_ONLY_READINESS_CHECK_LIVE_EXECUTION_DISABLED",
            simulation_only=True,
            live_execution_enabled=False,
        )
