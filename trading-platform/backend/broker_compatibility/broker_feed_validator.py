from backend.broker_compatibility.broker_feed_quality_models import BrokerSymbolFeedQuality
from backend.broker_compatibility.broker_observation_models import BrokerSymbolSnapshot
from backend.broker_compatibility.spread_quality_analyzer import SpreadQualityAnalyzer
from backend.broker_compatibility.tick_freshness_checker import TickFreshnessChecker


class BrokerFeedValidator:
    """Validate broker observation snapshots for feed quality."""

    def __init__(
        self,
        spread_analyzer: SpreadQualityAnalyzer | None = None,
        freshness_checker: TickFreshnessChecker | None = None,
    ) -> None:
        self.spread_analyzer = spread_analyzer or SpreadQualityAnalyzer()
        self.freshness_checker = freshness_checker or TickFreshnessChecker()

    def validate_snapshot(self, snapshot: BrokerSymbolSnapshot) -> BrokerSymbolFeedQuality:
        issues: list[str] = []
        spread_points = self._spread_points(snapshot)
        spread_quality = self.spread_analyzer.classify_spread(snapshot.canonical_symbol, spread_points)
        tick_fresh = self.freshness_checker.is_fresh(snapshot.timestamp)

        if not snapshot.available:
            issues.append("Symbol snapshot is unavailable.")
        if snapshot.bid is None:
            issues.append("Missing bid.")
        if snapshot.ask is None:
            issues.append("Missing ask.")
        if snapshot.bid is not None and snapshot.ask is not None and float(snapshot.ask) < float(snapshot.bid):
            issues.append("Ask is below bid.")
        if spread_quality == "INVALID":
            issues.append("Spread is invalid or missing.")
        elif spread_quality == "WIDE":
            issues.append("Spread is wide.")
        if not tick_fresh:
            issues.append("Tick is stale or timestamp is unavailable.")
        if snapshot.source == "UNAVAILABLE":
            issues.append("Broker observation source is unavailable.")

        feed_quality = self._feed_quality(snapshot, spread_quality, tick_fresh, issues)
        return BrokerSymbolFeedQuality(
            broker_id=snapshot.broker_id,
            canonical_symbol=snapshot.canonical_symbol,
            broker_symbol=snapshot.broker_symbol,
            available=snapshot.available,
            visible=snapshot.available,
            bid=snapshot.bid,
            ask=snapshot.ask,
            spread=spread_points,
            spread_quality=spread_quality,
            tick_fresh=tick_fresh,
            feed_quality=feed_quality,
            issues=issues,
            message=self._message(feed_quality, snapshot.canonical_symbol, issues),
            simulation_only=True,
            live_execution_enabled=False,
        )

    def _spread_points(self, snapshot: BrokerSymbolSnapshot) -> float | None:
        if snapshot.spread is None:
            if snapshot.bid is None or snapshot.ask is None:
                return None
            raw_spread = float(snapshot.ask) - float(snapshot.bid)
        else:
            raw_spread = float(snapshot.spread)
        point = float(snapshot.point or 0.0)
        if point > 0 and raw_spread < 1:
            return round(raw_spread / point, 4)
        return round(raw_spread, 4)

    def _feed_quality(self, snapshot: BrokerSymbolSnapshot, spread_quality: str, tick_fresh: bool, issues: list[str]) -> str:
        if not snapshot.available or snapshot.source == "UNAVAILABLE":
            return "UNAVAILABLE"
        if "Ask is below bid." in issues or spread_quality == "INVALID":
            return "INVALID"
        if not tick_fresh or spread_quality == "WIDE" or issues:
            return "WARNING"
        return "VALID"

    def _message(self, feed_quality: str, symbol: str, issues: list[str]) -> str:
        if feed_quality == "VALID":
            return f"{symbol} feed snapshot is valid for read-only demo observation."
        if feed_quality == "UNAVAILABLE":
            return f"{symbol} feed snapshot is unavailable."
        return f"{symbol} feed quality requires attention: {'; '.join(issues)}"
