from backend.broker_compatibility.broker_registry import BrokerRegistry
from backend.broker_compatibility.broker_symbol_mapper import BrokerSymbolMapper
from backend.broker_compatibility.mt5_demo_models import (
    BrokerDemoVerificationReport,
    BrokerSymbolVerification,
)
from backend.broker_compatibility.mt5_demo_readiness_checker import MT5DemoReadinessChecker
from backend.broker_compatibility.mt5_symbol_verifier import MT5SymbolVerifier


class BrokerSymbolVerificationReportBuilder:
    """Build broker-level MT5 demo symbol verification reports."""

    def __init__(
        self,
        registry: BrokerRegistry | None = None,
        mapper: BrokerSymbolMapper | None = None,
        readiness_checker: MT5DemoReadinessChecker | None = None,
        symbol_verifier: MT5SymbolVerifier | None = None,
    ) -> None:
        self.registry = registry or BrokerRegistry()
        self.mapper = mapper or BrokerSymbolMapper(self.registry)
        self.readiness_checker = readiness_checker or MT5DemoReadinessChecker()
        self.symbol_verifier = symbol_verifier or MT5SymbolVerifier()

    def build_report(self, broker_id: str) -> BrokerDemoVerificationReport:
        broker = self.registry.get_broker(broker_id)
        broker_id = str(broker_id or "").strip().upper()
        readiness = self.readiness_checker.check_terminal_readiness()
        if broker is None:
            return BrokerDemoVerificationReport(
                broker_id=broker_id,
                terminal_readiness=readiness,
                symbol_verifications=[],
                missing_symbols=["EURUSD", "XAUUSD", "NIFTY50"],
                ready_for_demo_observation=False,
                ready_for_demo_execution=False,
            )

        verifications: list[BrokerSymbolVerification] = []
        for mapping in self.mapper.list_symbol_mappings(broker.broker_id):
            if not mapping.supported:
                verifications.append(
                    BrokerSymbolVerification(
                        broker_id=broker.broker_id,
                        canonical_symbol=mapping.canonical_symbol,
                        expected_broker_symbol=mapping.broker_symbol,
                        verification_status="CONDITIONAL" if mapping.canonical_symbol == "NIFTY50" else "UNSUPPORTED",
                        message=mapping.notes,
                    )
                )
                continue
            verification = self.symbol_verifier.verify_symbol(
                mapping.canonical_symbol,
                mapping.broker_symbol,
                broker.broker_id,
            )
            verifications.append(verification)

        verified = [item.canonical_symbol for item in verifications if item.verification_status == "VERIFIED"]
        missing = [
            item.canonical_symbol
            for item in verifications
            if item.verification_status in {"NOT_FOUND", "MT5_UNAVAILABLE", "UNSUPPORTED"}
        ]
        conditional = [item.canonical_symbol for item in verifications if item.verification_status == "CONDITIONAL"]
        return BrokerDemoVerificationReport(
            broker_id=broker.broker_id,
            terminal_readiness=readiness,
            symbol_verifications=verifications,
            verified_symbols=verified,
            missing_symbols=missing,
            conditional_symbols=conditional,
            ready_for_demo_observation=readiness.initialized and bool(verified),
            ready_for_demo_execution=False,
            safety_status="READ_ONLY_SYMBOL_VERIFICATION_LIVE_EXECUTION_DISABLED",
            simulation_only=True,
            live_execution_enabled=False,
        )
