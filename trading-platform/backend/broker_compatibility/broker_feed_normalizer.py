from backend.broker_compatibility.broker_observation_models import BrokerSymbolSnapshot
from backend.broker_compatibility.canonical_feed_models import CanonicalMarketTick


class BrokerFeedNormalizer:
    """Normalize broker observation snapshots into canonical market ticks."""

    def normalize_snapshot(self, snapshot: BrokerSymbolSnapshot, market_type: str | None = None) -> CanonicalMarketTick:
        issues: list[str] = []
        bid = snapshot.bid
        ask = snapshot.ask
        usable = bool(snapshot.available and bid is not None and ask is not None and float(ask) >= float(bid))
        mid = None
        if usable:
            mid = round((float(bid) + float(ask)) / 2.0, int(snapshot.digits or 5))
        else:
            if not snapshot.available:
                issues.append("Snapshot is unavailable.")
            if bid is None:
                issues.append("Missing bid.")
            if ask is None:
                issues.append("Missing ask.")
            if bid is not None and ask is not None and float(ask) < float(bid):
                issues.append("Ask is below bid.")

        return CanonicalMarketTick(
            canonical_symbol=snapshot.canonical_symbol,
            broker_id=snapshot.broker_id,
            broker_symbol=snapshot.broker_symbol,
            bid=bid,
            ask=ask,
            mid=mid,
            spread=snapshot.spread,
            digits=snapshot.digits,
            point=snapshot.point,
            market_type=market_type,
            timestamp=snapshot.timestamp,
            source=snapshot.source,
            usable=usable,
            quality="UNAVAILABLE" if snapshot.source == "UNAVAILABLE" else ("WARNING" if not usable else "GOOD"),
            issues=issues,
            simulation_only=True,
            live_execution_enabled=False,
        )
