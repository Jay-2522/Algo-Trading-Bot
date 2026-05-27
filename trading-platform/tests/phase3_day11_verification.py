import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def verify_files_and_routes() -> bool:
    files = [
        "backend/broker_compatibility/canonical_candle_models.py",
        "backend/broker_compatibility/mt5_candle_fetcher.py",
        "backend/broker_compatibility/candle_normalizer.py",
        "backend/broker_compatibility/multi_timeframe_feed_engine.py",
        "backend/broker_compatibility/candle_stream_quality_checker.py",
        "backend/broker_compatibility/canonical_candle_feed_service.py",
        "docs/phase-3-day-11-progress.md",
    ]
    files_ok = all((PROJECT_ROOT / path).is_file() for path in files)
    try:
        from backend.main import app

        routes = {route.path for route in app.routes}
        expected = {
            "/brokers/candles/status",
            "/brokers/candles/all",
            "/brokers/{broker_id}/candles/{symbol}",
            "/brokers/{broker_id}/candles/{symbol}/{timeframe}",
            "/brokers/feed-quality/status",
            "/brokers/canonical-feed/status",
        }
        routes_ok = expected <= routes
    except Exception:
        routes_ok = False
    return show("Candle feed files and routes exist", files_ok and routes_ok)


def verify_fetcher_and_timeframes() -> bool:
    try:
        from backend.broker_compatibility.mt5_candle_fetcher import MT5CandleFetcher

        fetcher = MT5CandleFetcher(force_fallback=True)
        candles = fetcher.fetch_candles("EURUSD", "M15", count=25)
        passed = (
            set(MT5CandleFetcher.SUPPORTED_TIMEFRAMES) == {"M5", "M15", "H1", "H4"}
            and len(candles) == 25
            and candles[0]["source"] == "SIMULATION_FALLBACK"
            and {"timestamp", "open", "high", "low", "close", "volume"} <= set(candles[0])
        )
        return show("MT5 fetcher safely falls back and supports required timeframes", passed)
    except Exception as exc:
        return show("MT5 fetcher safely falls back and supports required timeframes", False, str(exc))


def verify_normalizer_and_quality() -> bool:
    try:
        from backend.broker_compatibility.candle_normalizer import CandleNormalizer
        from backend.broker_compatibility.candle_stream_quality_checker import CandleStreamQualityChecker

        normalizer = CandleNormalizer()
        checker = CandleStreamQualityChecker()
        candle = normalizer.normalize_candle(
            {
                "timestamp": "2024-01-01T00:00:00+00:00",
                "open": 1.1,
                "high": 1.101,
                "low": 1.099,
                "close": 1.1005,
                "volume": 100,
                "source": "SIMULATION_FALLBACK",
            },
            "eur/usd",
            "STARTRADER",
            "M15",
        )
        invalid = normalizer.normalize_candle(
            {
                "timestamp": "2024-01-01T00:00:00+00:00",
                "open": 1.1,
                "high": 1.099,
                "low": 1.101,
                "close": 1.1005,
                "source": "MT5_READ_ONLY",
            },
            "EURUSD",
            "STARTRADER",
            "M15",
        )
        passed = (
            candle.canonical_symbol == "EURUSD"
            and candle.usable is True
            and candle.quality == "WARNING"
            and checker.classify_candle_quality(candle) == "WARNING"
            and invalid.usable is False
            and checker.classify_candle_quality(invalid) == "INVALID"
            and invalid.simulation_only is True
            and invalid.live_execution_enabled is False
        )
        return show("Candle normalization preserves OHLC integrity and quality", passed)
    except Exception as exc:
        return show("Candle normalization preserves OHLC integrity and quality", False, str(exc))


def verify_feed_engine_and_service() -> bool:
    try:
        from backend.broker_compatibility.canonical_candle_feed_service import CanonicalCandleFeedService
        from backend.broker_compatibility.mt5_candle_fetcher import MT5CandleFetcher
        from backend.broker_compatibility.multi_timeframe_feed_engine import MultiTimeframeFeedEngine

        engine = MultiTimeframeFeedEngine(fetcher=MT5CandleFetcher(force_fallback=True))
        report = engine.build_symbol_feed("STARTRADER", "XAUUSD")
        timeframe_report = engine.build_timeframe_feed("STARTRADER", "NIFTY50", "H1")
        service = CanonicalCandleFeedService(feed_engine=engine)
        status = service.get_status()
        passed = (
            report.canonical_symbol == "XAUUSD"
            and set(report.timeframes) == {"M5", "M15", "H1", "H4"}
            and all(len(report.candles[tf]) == 100 for tf in report.timeframes)
            and report.ai_ready is True
            and report.overall_quality == "WARNING"
            and timeframe_report.timeframes == ["H1"]
            and timeframe_report.ai_ready is True
            and status["simulation_only"] is True
            and status["live_execution_enabled"] is False
            and "M15" in status["supported_timeframes"]
        )
        return show("Multi-timeframe feed engine and service build JSON-safe reports", passed)
    except Exception as exc:
        return show("Multi-timeframe feed engine and service build JSON-safe reports", False, str(exc))


def verify_api_and_safety() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        status = client.get("/brokers/candles/status")
        symbol_feed = client.get("/brokers/STARTRADER/candles/EURUSD")
        timeframe_feed = client.get("/brokers/STARTRADER/candles/XAUUSD/H1")
        day9 = client.get("/brokers/feed-quality/status")
        day10 = client.get("/brokers/canonical-feed/status")
        payload = timeframe_feed.json()
        safety_text = "\n".join(
            path.read_text(encoding="utf-8", errors="ignore")
            for path in (PROJECT_ROOT / "backend").rglob("*.py")
        )
        passed = (
            status.status_code == 200
            and status.json()["simulation_only"] is True
            and status.json()["live_execution_enabled"] is False
            and symbol_feed.status_code == 200
            and symbol_feed.json()["simulation_only"] is True
            and symbol_feed.json()["live_execution_enabled"] is False
            and timeframe_feed.status_code == 200
            and payload["timeframes"] == ["H1"]
            and len(payload["candles"]["H1"]) > 0
            and payload["candles"]["H1"][0]["simulation_only"] is True
            and payload["candles"]["H1"][0]["live_execution_enabled"] is False
            and day9.status_code == 200
            and day10.status_code == 200
            and "mt5.order_send" not in safety_text
            and "order_send(" not in safety_text
            and "live_execution_enabled=True" not in safety_text
        )
        return show("Candle feed API is JSON-safe and preserves prior broker routes", passed)
    except Exception as exc:
        return show("Candle feed API is JSON-safe and preserves prior broker routes", False, str(exc))


def main() -> int:
    print("Phase 3 Day 11 Candle Feed Verification")
    print("=" * 50)
    checks = [
        verify_files_and_routes(),
        verify_fetcher_and_timeframes(),
        verify_normalizer_and_quality(),
        verify_feed_engine_and_service(),
        verify_api_and_safety(),
    ]
    print("=" * 50)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
