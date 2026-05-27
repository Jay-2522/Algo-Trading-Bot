import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def snapshot(symbol: str, bid=1.1, ask=1.10002, spread=None, point=0.00001, available=True):
    from backend.broker_compatibility.broker_observation_models import BrokerSymbolSnapshot

    calculated_spread = spread
    if calculated_spread is None and bid is not None and ask is not None:
        calculated_spread = ask - bid
    return BrokerSymbolSnapshot(
        broker_id="STARTRADER",
        canonical_symbol=symbol,
        broker_symbol=symbol,
        bid=bid,
        ask=ask,
        spread=calculated_spread,
        digits=5 if symbol == "EURUSD" else 2,
        point=point,
        timestamp=datetime.now(timezone.utc),
        source="SIMULATION_FALLBACK" if available else "UNAVAILABLE",
        available=available,
        message="Synthetic test snapshot.",
    )


def verify_files_and_routes() -> bool:
    files = [
        "backend/broker_compatibility/broker_feed_quality_models.py",
        "backend/broker_compatibility/spread_quality_analyzer.py",
        "backend/broker_compatibility/tick_freshness_checker.py",
        "backend/broker_compatibility/broker_feed_validator.py",
        "backend/broker_compatibility/broker_feed_quality_report_builder.py",
        "backend/broker_compatibility/broker_feed_quality_service.py",
        "docs/phase-3-day-9-progress.md",
    ]
    files_ok = all((PROJECT_ROOT / path).is_file() for path in files)
    try:
        from backend.main import app

        routes = {route.path for route in app.routes}
        expected = {
            "/brokers/feed-quality/status",
            "/brokers/feed-quality/all",
            "/brokers/{broker_id}/feed-quality",
            "/brokers/{broker_id}/feed-quality/{symbol}",
            "/brokers/observation/status",
            "/brokers/{broker_id}/observation",
        }
        routes_ok = expected <= routes
    except Exception:
        routes_ok = False
    return show("Feed quality files and routes exist", files_ok and routes_ok)


def verify_spread_and_freshness() -> bool:
    try:
        from backend.broker_compatibility.spread_quality_analyzer import SpreadQualityAnalyzer
        from backend.broker_compatibility.tick_freshness_checker import TickFreshnessChecker

        analyzer = SpreadQualityAnalyzer()
        checker = TickFreshnessChecker()
        passed = (
            analyzer.classify_spread("EURUSD", 2) == "EXCELLENT"
            and analyzer.classify_spread("EURUSD", 5) == "GOOD"
            and analyzer.classify_spread("EURUSD", 10) == "ACCEPTABLE"
            and analyzer.classify_spread("EURUSD", 11) == "WIDE"
            and analyzer.classify_spread("XAUUSD", 20) == "GOOD"
            and analyzer.classify_spread("XAUUSD", 50) == "ACCEPTABLE"
            and analyzer.classify_spread("XAUUSD", 51) == "WIDE"
            and analyzer.classify_spread("NIFTY50", 5) == "GOOD"
            and analyzer.classify_spread("NIFTY50", 15) == "ACCEPTABLE"
            and analyzer.classify_spread("NIFTY50", None) == "INVALID"
            and checker.is_fresh(datetime.now(timezone.utc), 30) is True
            and checker.is_fresh(datetime.now(timezone.utc) - timedelta(seconds=60), 30) is False
            and checker.is_fresh(None, 30) is False
        )
        return show("Spread quality and tick freshness classifiers work", passed)
    except Exception as exc:
        return show("Spread quality and tick freshness classifiers work", False, str(exc))


def verify_validator_and_report_builder() -> bool:
    try:
        from backend.broker_compatibility.broker_feed_quality_report_builder import BrokerFeedQualityReportBuilder
        from backend.broker_compatibility.broker_feed_validator import BrokerFeedValidator

        validator = BrokerFeedValidator()
        valid_eur = validator.validate_snapshot(snapshot("EURUSD", bid=1.1, ask=1.10002, point=0.00001))
        invalid = validator.validate_snapshot(snapshot("EURUSD", bid=1.1, ask=1.0999, point=0.00001))
        unavailable_nifty = validator.validate_snapshot(
            snapshot("NIFTY50", bid=None, ask=None, spread=None, point=0.01, available=False)
        )
        report = BrokerFeedQualityReportBuilder(validator).build_report(
            "STARTRADER",
            [
                snapshot("EURUSD", bid=1.1, ask=1.10002, point=0.00001),
                snapshot("XAUUSD", bid=2400.0, ask=2400.2, point=0.01),
                snapshot("NIFTY50", bid=None, ask=None, spread=None, point=0.01, available=False),
            ],
        )
        passed = (
            valid_eur.feed_quality == "VALID"
            and valid_eur.spread_quality == "EXCELLENT"
            and invalid.feed_quality == "INVALID"
            and unavailable_nifty.feed_quality == "UNAVAILABLE"
            and report.ready_for_demo_observation is True
            and report.ready_for_demo_execution is False
            and report.simulation_only is True
            and report.live_execution_enabled is False
            and "NIFTY50" in report.unavailable_symbols
            and report.overall_quality in {"WARNING", "GOOD"}
        )
        return show("Feed validator and report builder handle valid/invalid/unavailable snapshots", passed)
    except Exception as exc:
        return show("Feed validator and report builder handle valid/invalid/unavailable snapshots", False, str(exc))


def verify_service_and_api_safety() -> bool:
    try:
        from backend.broker_compatibility.broker_feed_quality_service import BrokerFeedQualityService
        from backend.main import app

        service = BrokerFeedQualityService()
        status = service.get_status()
        symbol_quality = service.check_symbol_feed("STARTRADER", "NIFTY50")
        client = TestClient(app)
        api_status = client.get("/brokers/feed-quality/status")
        all_reports = client.get("/brokers/feed-quality/all")
        broker_report = client.get("/brokers/STARTRADER/feed-quality")
        eur = client.get("/brokers/STARTRADER/feed-quality/EURUSD")
        xau = client.get("/brokers/STARTRADER/feed-quality/XAUUSD")
        nifty = client.get("/brokers/STARTRADER/feed-quality/NIFTY50")
        observation = client.get("/brokers/STARTRADER/observation")
        safety = client.get("/system/safety-scan").json()
        passed = (
            status["simulation_only"] is True
            and status["live_execution_enabled"] is False
            and symbol_quality.simulation_only is True
            and symbol_quality.live_execution_enabled is False
            and api_status.status_code == 200
            and api_status.json()["simulation_only"] is True
            and api_status.json()["live_execution_enabled"] is False
            and all_reports.status_code == 200
            and len(all_reports.json()) == 3
            and broker_report.status_code == 200
            and broker_report.json()["ready_for_demo_execution"] is False
            and broker_report.json()["simulation_only"] is True
            and broker_report.json()["live_execution_enabled"] is False
            and eur.status_code == 200
            and xau.status_code == 200
            and nifty.status_code == 200
            and nifty.json()["feed_quality"] == "UNAVAILABLE"
            and observation.status_code == 200
            and safety["passed"] is True
            and safety["order_send_found"] is False
            and safety["live_execution_enabled"] is False
        )
        return show("Feed quality service and API are JSON-safe and preserve observation routes", passed)
    except Exception as exc:
        return show("Feed quality service and API are JSON-safe and preserve observation routes", False, str(exc))


def main() -> int:
    print("Phase 3 Day 9 Broker Feed Quality Verification")
    print("=" * 54)
    checks = [
        verify_files_and_routes(),
        verify_spread_and_freshness(),
        verify_validator_and_report_builder(),
        verify_service_and_api_safety(),
    ]
    print("=" * 54)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
