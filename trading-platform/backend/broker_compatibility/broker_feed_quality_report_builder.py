from backend.broker_compatibility.broker_feed_quality_models import BrokerFeedQualityReport
from backend.broker_compatibility.broker_feed_validator import BrokerFeedValidator
from backend.broker_compatibility.broker_observation_models import BrokerSymbolSnapshot


class BrokerFeedQualityReportBuilder:
    """Build broker feed quality reports from observation snapshots."""

    def __init__(self, validator: BrokerFeedValidator | None = None) -> None:
        self.validator = validator or BrokerFeedValidator()

    def build_report(self, broker_id: str, snapshots: list[BrokerSymbolSnapshot]) -> BrokerFeedQualityReport:
        qualities = [self.validator.validate_snapshot(snapshot) for snapshot in snapshots]
        valid = [item.canonical_symbol for item in qualities if item.feed_quality == "VALID"]
        warning = [item.canonical_symbol for item in qualities if item.feed_quality == "WARNING"]
        invalid = [item.canonical_symbol for item in qualities if item.feed_quality == "INVALID"]
        unavailable = [item.canonical_symbol for item in qualities if item.feed_quality == "UNAVAILABLE"]

        if not qualities or len(unavailable) == len(qualities):
            overall = "UNAVAILABLE"
        elif invalid:
            overall = "INVALID"
        elif warning or unavailable:
            overall = "WARNING"
        else:
            overall = "GOOD"

        ready_observation = "EURUSD" in valid and "XAUUSD" in valid
        if "NIFTY50" in [item.canonical_symbol for item in qualities] and "NIFTY50" not in valid:
            if "NIFTY50" not in unavailable:
                unavailable.append("NIFTY50")

        return BrokerFeedQualityReport(
            broker_id=str(broker_id or "").strip().upper(),
            symbol_qualities=qualities,
            valid_symbols=valid,
            warning_symbols=warning,
            invalid_symbols=invalid,
            unavailable_symbols=unavailable,
            overall_quality=overall,
            ready_for_demo_observation=ready_observation,
            ready_for_demo_execution=False,
            safety_status="READ_ONLY_FEED_VALIDATION_ONLY_LIVE_EXECUTION_DISABLED",
            simulation_only=True,
            live_execution_enabled=False,
        )
