import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def snapshot(symbol: str, bid=1.1, ask=1.1002, available=True):
    from backend.broker_compatibility.broker_observation_models import BrokerSymbolSnapshot

    return BrokerSymbolSnapshot(
        broker_id="STARTRADER",
        canonical_symbol=symbol,
        broker_symbol=symbol,
        bid=bid,
        ask=ask,
        spread=(ask - bid) if bid is not None and ask is not None else None,
        digits=5 if symbol == "EURUSD" else 2,
        point=0.00001 if symbol == "EURUSD" else 0.01,
        timestamp=datetime.now(timezone.utc),
        source="SIMULATION_FALLBACK" if available else "UNAVAILABLE",
        available=available,
        message="Synthetic canonical feed test snapshot.",
    )


def verify_files_and_routes() -> bool:
    files = [
        "backend/broker_compatibility/canonical_feed_models.py",
        "backend/broker_compatibility/broker_feed_normalizer.py",
        "backend/broker_compatibility/canonical_market_feed_builder.py",
        "backend/broker_compatibility/canonical_feed_quality_resolver.py",
        "backend/broker_compatibility/canonical_feed_service.py",
        "docs/phase-3-day-10-progress.md",
    ]
    files_ok = all((PROJECT_ROOT / path).is_file() for path in files)
    try:
        from backend.main import app

        routes = {route.path for route in app.routes}
        expected = {
            "/brokers/canonical-feed/status",
            "/brokers/canonical-feed/all",
            "/brokers/{broker_id}/canonical-feed",
            "/brokers/{broker_id}/canonical-feed/{symbol}",
            "/brokers/feed-quality/status",
            "/brokers/{broker_id}/feed-quality",
        }
        routes_ok = expected <= routes
    except Exception:
        routes_ok = False
    return show("Canonical feed files and routes exist", files_ok and routes_ok)


def verify_normalizer_and_quality() -> bool:
    try:
        from backend.broker_compatibility.broker_feed_normalizer import BrokerFeedNormalizer
        from backend.broker_compatibility.canonical_feed_quality_resolver import CanonicalFeedQualityResolver

        normalizer = BrokerFeedNormalizer()
        resolver = CanonicalFeedQualityResolver()
        tick = normalizer.normalize_snapshot(snapshot("EURUSD", 1.1, 1.1002), market_type="FOREX")
        resolved = resolver.resolve_tick_quality(tick)
        unavailable = resolver.resolve_tick_quality(
            normalizer.normalize_snapshot(snapshot("NIFTY50", None, None, available=False), market_type="INDIAN_INDEX")
        )
        invalid = resolver.resolve_tick_quality(
            normalizer.normalize_snapshot(snapshot("EURUSD", 1.1002, 1.1), market_type="FOREX")
        )
        passed = (
            tick.mid == 1.1001
            and tick.usable is True
            and tick.market_type == "FOREX"
            and resolved.quality in {"GOOD", "WARNING"}
            and unavailable.usable is False
            and unavailable.quality == "UNAVAILABLE"
            and invalid.usable is False
            and invalid.quality == "INVALID"
            and unavailable.simulation_only is True
            and unavailable.live_execution_enabled is False
        )
        return show("Normalizer calculates mid and quality resolver classifies ticks", passed)
    except Exception as exc:
        return show("Normalizer calculates mid and quality resolver classifies ticks", False, str(exc))


def verify_builder_and_service() -> bool:
    try:
        from backend.broker_compatibility.broker_observation_service import BrokerObservationService
        from backend.broker_compatibility.broker_symbol_snapshotter import BrokerSymbolSnapshotter
        from backend.broker_compatibility.canonical_feed_service import CanonicalFeedService
        from backend.broker_compatibility.canonical_market_feed_builder import CanonicalMarketFeedBuilder

        class StaticSnapshotter(BrokerSymbolSnapshotter):
            def snapshot_all_symbols(self, broker_id: str):
                return [
                    snapshot("EURUSD", 1.1, 1.10002),
                    snapshot("XAUUSD", 2400.0, 2400.2),
                    snapshot("NIFTY50", None, None, available=False),
                ]

            def snapshot_symbol(self, broker_id: str, canonical_symbol: str):
                if canonical_symbol.upper() == "NIFTY50":
                    return snapshot("NIFTY50", None, None, available=False)
                return snapshot(canonical_symbol.upper(), 1.1, 1.10002)

        observation = BrokerObservationService(snapshotter=StaticSnapshotter())
        builder = CanonicalMarketFeedBuilder(observation_service=observation)
        report = builder.build_feed_for_broker("STARTRADER")
        service = CanonicalFeedService(builder=builder)
        status = service.get_status()
        symbol = service.get_symbol_feed("STARTRADER", "NIFTY50")
        passed = (
            report.broker_id == "STARTRADER"
            and len(report.ticks) == 3
            and "EURUSD" in report.usable_symbols
            and "XAUUSD" in report.usable_symbols
            and "NIFTY50" in report.unusable_symbols
            and report.ai_ready is True
            and report.ready_for_demo_execution is False if hasattr(report, "ready_for_demo_execution") else True
            and report.simulation_only is True
            and report.live_execution_enabled is False
            and status["simulation_only"] is True
            and status["live_execution_enabled"] is False
            and symbol.quality == "UNAVAILABLE"
        )
        return show("Canonical feed builder and service produce JSON-safe AI-ready reports", passed)
    except Exception as exc:
        return show("Canonical feed builder and service produce JSON-safe AI-ready reports", False, str(exc))


def verify_api_and_safety() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        status = client.get("/brokers/canonical-feed/status")
        all_feeds = client.get("/brokers/canonical-feed/all")
        broker_feed = client.get("/brokers/STARTRADER/canonical-feed")
        eur = client.get("/brokers/STARTRADER/canonical-feed/EURUSD")
        xau = client.get("/brokers/STARTRADER/canonical-feed/XAUUSD")
        nifty = client.get("/brokers/STARTRADER/canonical-feed/NIFTY50")
        feed_quality = client.get("/brokers/feed-quality/status")
        safety = client.get("/system/safety-scan").json()
        passed = (
            status.status_code == 200
            and status.json()["simulation_only"] is True
            and status.json()["live_execution_enabled"] is False
            and all_feeds.status_code == 200
            and len(all_feeds.json()) == 3
            and broker_feed.status_code == 200
            and broker_feed.json()["simulation_only"] is True
            and broker_feed.json()["live_execution_enabled"] is False
            and eur.status_code == 200
            and xau.status_code == 200
            and nifty.status_code == 200
            and nifty.json()["usable"] is False
            and nifty.json()["quality"] == "UNAVAILABLE"
            and feed_quality.status_code == 200
            and safety["passed"] is True
            and safety["order_send_found"] is False
            and safety["live_execution_enabled"] is False
        )
        return show("Canonical feed API is JSON-safe and preserves Day 9 routes", passed)
    except Exception as exc:
        return show("Canonical feed API is JSON-safe and preserves Day 9 routes", False, str(exc))


def main() -> int:
    print("Phase 3 Day 10 Canonical Feed Verification")
    print("=" * 50)
    checks = [
        verify_files_and_routes(),
        verify_normalizer_and_quality(),
        verify_builder_and_service(),
        verify_api_and_safety(),
    ]
    print("=" * 50)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
