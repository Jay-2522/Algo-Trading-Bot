from backend.broker_compatibility.broker_feed_validator import BrokerFeedValidator
from backend.broker_compatibility.broker_observation_models import BrokerSymbolSnapshot
from backend.broker_compatibility.canonical_feed_models import CanonicalMarketTick


class CanonicalFeedQualityResolver:
    """Resolve canonical feed tick quality using Day 9 validation rules."""

    def __init__(self, feed_validator: BrokerFeedValidator | None = None) -> None:
        self.feed_validator = feed_validator or BrokerFeedValidator()

    def resolve_tick_quality(self, tick: CanonicalMarketTick) -> CanonicalMarketTick:
        if not tick.usable:
            tick.quality = "UNAVAILABLE" if tick.source == "UNAVAILABLE" else "INVALID"
            if not tick.issues:
                tick.issues.append("Canonical tick is not usable.")
            return tick

        snapshot = BrokerSymbolSnapshot(
            broker_id=tick.broker_id,
            canonical_symbol=tick.canonical_symbol,
            broker_symbol=tick.broker_symbol,
            bid=tick.bid,
            ask=tick.ask,
            spread=tick.spread,
            digits=tick.digits,
            point=tick.point,
            timestamp=tick.timestamp,
            source=tick.source if tick.source in {"MT5_READ_ONLY", "SIMULATION_FALLBACK", "UNAVAILABLE"} else "UNAVAILABLE",
            available=tick.usable,
            message="Canonical feed quality resolution snapshot.",
        )
        quality = self.feed_validator.validate_snapshot(snapshot)
        if quality.feed_quality == "VALID":
            tick.quality = "GOOD"
        elif quality.feed_quality == "WARNING":
            tick.quality = "WARNING"
        elif quality.feed_quality == "INVALID":
            tick.quality = "INVALID"
        else:
            tick.quality = "UNAVAILABLE"
        tick.issues = list(dict.fromkeys(tick.issues + quality.issues))
        return tick
