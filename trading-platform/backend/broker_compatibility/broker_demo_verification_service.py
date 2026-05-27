from backend.broker_compatibility.broker_registry import BrokerRegistry
from backend.broker_compatibility.broker_symbol_mapper import BrokerSymbolMapper
from backend.broker_compatibility.broker_symbol_verification_report import BrokerSymbolVerificationReportBuilder
from backend.broker_compatibility.mt5_demo_models import (
    BrokerDemoVerificationReport,
    BrokerSymbolVerification,
    MT5TerminalReadiness,
)
from backend.broker_compatibility.mt5_demo_readiness_checker import MT5DemoReadinessChecker
from backend.broker_compatibility.mt5_symbol_verifier import MT5SymbolVerifier


class BrokerDemoVerificationService:
    """Read-only MT5 demo-readiness and broker symbol verification facade."""

    def __init__(
        self,
        registry: BrokerRegistry | None = None,
        mapper: BrokerSymbolMapper | None = None,
        readiness_checker: MT5DemoReadinessChecker | None = None,
        symbol_verifier: MT5SymbolVerifier | None = None,
        report_builder: BrokerSymbolVerificationReportBuilder | None = None,
    ) -> None:
        self.registry = registry or BrokerRegistry()
        self.mapper = mapper or BrokerSymbolMapper(self.registry)
        self.readiness_checker = readiness_checker or MT5DemoReadinessChecker()
        self.symbol_verifier = symbol_verifier or MT5SymbolVerifier()
        self.report_builder = report_builder or BrokerSymbolVerificationReportBuilder(
            self.registry,
            self.mapper,
            self.readiness_checker,
            self.symbol_verifier,
        )

    def get_mt5_readiness(self) -> MT5TerminalReadiness:
        return self.readiness_checker.check_terminal_readiness()

    def verify_broker_symbols(self, broker_id: str) -> BrokerDemoVerificationReport:
        return self.report_builder.build_report(broker_id)

    def verify_all_brokers(self) -> list[BrokerDemoVerificationReport]:
        return [self.verify_broker_symbols(broker.broker_id) for broker in self.registry.list_brokers()]

    def verify_symbol_for_broker(self, broker_id: str, symbol: str) -> BrokerSymbolVerification:
        broker = self.registry.get_broker(broker_id)
        if broker is None:
            return BrokerSymbolVerification(
                broker_id=str(broker_id or "").strip().upper(),
                canonical_symbol=str(symbol or "").strip().upper(),
                expected_broker_symbol=None,
                verification_status="UNSUPPORTED",
                message="Broker is not registered.",
            )
        mapping = self.mapper.map_symbol(broker.broker_id, symbol)
        if not mapping.supported:
            return BrokerSymbolVerification(
                broker_id=broker.broker_id,
                canonical_symbol=mapping.canonical_symbol,
                expected_broker_symbol=mapping.broker_symbol,
                verification_status="CONDITIONAL" if mapping.canonical_symbol == "NIFTY50" else "UNSUPPORTED",
                message=mapping.notes,
            )
        return self.symbol_verifier.verify_symbol(mapping.canonical_symbol, mapping.broker_symbol, broker.broker_id)
