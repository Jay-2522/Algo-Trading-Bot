import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def print_result(name: str, passed: bool, detail: str = "") -> None:
    status = "PASS" if passed else "FAIL"
    suffix = f" - {detail}" if detail else ""
    print(f"[{status}] {name}{suffix}")


def verify_path(path: str, label: str) -> bool:
    passed = (PROJECT_ROOT / path).is_file()
    print_result(label, passed, "" if passed else path)
    return passed


def candle(hour: int, minute: int, high: float, low: float, close: float, open_price: float = 100.0) -> dict:
    return {
        "time": datetime(2026, 5, 26, hour, minute, tzinfo=timezone.utc),
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
    }


def session_candles() -> list[dict]:
    return [
        candle(1, 0, 101.0, 99.0, 100.0),
        candle(2, 0, 102.0, 98.0, 100.0),
        candle(9, 15, 103.0, 100.0, 101.5),
        candle(9, 30, 102.0, 99.0, 101.0),
        candle(12, 15, 101.0, 97.0, 99.0),
        candle(13, 0, 101.0, 98.0, 100.0),
    ]


def sweep_context() -> dict:
    return {"sweeps": [{"direction": "BEARISH", "valid": True, "strength": 85.0}]}


def verify_routes() -> bool:
    try:
        from backend.main import app

        required = {
            "/institutional/alignment/{symbol}",
            "/institutional/session/{symbol}",
            "/institutional/session/ranges/{symbol}",
            "/institutional/session/killzone/{symbol}",
            "/institutional/session/liquidity/{symbol}",
            "/institutional/session/manipulation/{symbol}",
            "/institutional/session/readiness/{symbol}",
        }
        paths = {route.path for route in app.routes}
        missing = sorted(required - paths)
        passed = not missing
        print_result("Session routes and existing alignment route remain registered", passed, str(missing))
        return passed
    except Exception as exc:
        print_result("FastAPI imports with session routes", False, str(exc))
        return False


def verify_ranges_and_killzones() -> bool:
    try:
        from backend.institutional_intelligence.killzone_detector import KillzoneDetector
        from backend.institutional_intelligence.session_range_detector import SessionRangeDetector

        ranges = SessionRangeDetector().detect_all_session_ranges(session_candles())
        detector = KillzoneDetector()
        london = detector.get_active_killzone(datetime(2026, 5, 26, 9, 30, tzinfo=timezone.utc))
        new_york = detector.get_active_killzone(datetime(2026, 5, 26, 13, 0, tzinfo=timezone.utc))
        outside = detector.get_active_killzone(datetime(2026, 5, 26, 22, 0, tzinfo=timezone.utc))
        passed = (
            ranges["ASIAN"].valid
            and ranges["ASIAN"].high == 102.0
            and ranges["ASIAN"].low == 98.0
            and ranges["LONDON"].valid
            and ranges["NEW_YORK"].valid
            and london.killzone_name == "LONDON_OPEN"
            and new_york.killzone_name == "NEW_YORK_OPEN"
            and outside.killzone_name == "NONE"
        )
        print_result("UTC ranges and killzone timing are deterministic", passed)
        return passed
    except Exception as exc:
        print_result("UTC ranges and killzone timing are deterministic", False, str(exc))
        return False


def verify_manipulation_and_quality() -> bool:
    try:
        from backend.institutional_intelligence.session_context_builder import SessionContextBuilder

        context = SessionContextBuilder().build_session_context(
            "XAUUSD",
            "M15",
            session_candles(),
            sweep_context=sweep_context(),
            news_status={"active_blackout": False, "trading_allowed": True},
            current_time_utc=datetime(2026, 5, 26, 9, 30, tzinfo=timezone.utc),
        )
        types = {signal.manipulation_type for signal in context.manipulation_signals}
        passed = (
            "ASIAN_HIGH_SWEEP" in types
            and "LONDON_FAKEOUT" in types
            and context.liquidity_profile.liquidity_quality == "HIGH"
            and context.session_quality_score >= 70.0
            and context.trade_timing_readiness == "HIGH_QUALITY_WINDOW"
        )
        print_result("Asian-range raid creates confirmed London manipulation timing quality", passed)
        return passed
    except Exception as exc:
        print_result("Asian-range raid creates confirmed London manipulation timing quality", False, str(exc))
        return False


def verify_news_and_alignment_guards() -> bool:
    try:
        from backend.institutional_intelligence.session_context_builder import SessionContextBuilder

        builder = SessionContextBuilder()
        news_blocked = builder.build_session_context(
            "XAUUSD",
            "M15",
            session_candles(),
            sweep_context=sweep_context(),
            news_status={"active_blackout": True, "trading_allowed": False},
            current_time_utc=datetime(2026, 5, 26, 9, 30, tzinfo=timezone.utc),
        )
        conflicted = builder.build_session_context(
            "XAUUSD",
            "M15",
            session_candles(),
            sweep_context=sweep_context(),
            alignment_context={"overall_direction": "CONFLICTED"},
            confluence_context={"confluence_score": {"dominant_direction": "CONFLICTED"}},
            current_time_utc=datetime(2026, 5, 26, 9, 30, tzinfo=timezone.utc),
        )
        passed = (
            news_blocked.trade_timing_readiness == "AVOID_NEWS_WINDOW"
            and news_blocked.session_quality_score < conflicted.session_quality_score
            and conflicted.trade_timing_readiness == "NORMAL_MONITORING"
            and len(conflicted.warnings) >= 2
        )
        print_result("News blackout and institutional conflict prevent high-quality readiness", passed)
        return passed
    except Exception as exc:
        print_result("News blackout and institutional conflict prevent high-quality readiness", False, str(exc))
        return False


def verify_malformed_and_service_fallback() -> bool:
    try:
        from backend.institutional_intelligence.session_models import SessionIntelligenceContext
        from backend.institutional_intelligence.session_range_detector import SessionRangeDetector
        from backend.institutional_intelligence.smc_service import SMCService

        invalid_range = SessionRangeDetector().detect_session_range([{"time": "bad", "high": "x"}], "ASIAN")

        class UnavailableData:
            def get_candles(self, *args, **kwargs):
                raise RuntimeError("No MT5 required for session verification.")

            def close(self):
                return None

        context = SMCService(market_data_service=UnavailableData()).analyze_session_intelligence("XAUUSD")
        passed = (
            not invalid_range.valid
            and isinstance(context, SessionIntelligenceContext)
            and context.symbol == "XAUUSD"
            and context.session_quality_score >= 0.0
            and context.trade_timing_readiness in {"AVOID_LOW_LIQUIDITY", "WAIT_FOR_KILLZONE"}
        )
        print_result("Malformed data and unavailable MT5 degrade safely", passed)
        return passed
    except Exception as exc:
        print_result("Malformed data and unavailable MT5 degrade safely", False, str(exc))
        return False


def verify_api_json_and_health() -> bool:
    try:
        from backend.api import institutional_routes
        from backend.institutional_intelligence.smc_service import SMCService
        from backend.main import app

        class UnavailableData:
            def get_candles(self, *args, **kwargs):
                raise RuntimeError("API verification does not require MT5.")

            def close(self):
                return None

        client = TestClient(app)
        original = institutional_routes.smc_service
        institutional_routes.smc_service = SMCService(market_data_service=UnavailableData())
        try:
            endpoints = [
                "/institutional/session/XAUUSD",
                "/institutional/session/ranges/XAUUSD",
                "/institutional/session/killzone/XAUUSD",
                "/institutional/session/liquidity/XAUUSD",
                "/institutional/session/manipulation/XAUUSD",
                "/institutional/session/readiness/XAUUSD",
            ]
            responses = [client.get(endpoint) for endpoint in endpoints]
            readiness = client.get("/system/readiness")
        finally:
            institutional_routes.smc_service = original
        timing = responses[-1].json()
        passed = (
            all(response.status_code == 200 for response in responses)
            and "session_quality_score" in responses[0].json()
            and len(responses[1].json()) == 3
            and timing["simulation_only"] is True
            and timing["live_execution_enabled"] is False
            and any(
                module["module_name"] == "institutional_session_intelligence"
                for module in readiness.json()["modules"]
            )
        )
        print_result("Session APIs are JSON-safe, analysis-only, and readiness monitored", passed)
        return passed
    except Exception as exc:
        print_result("Session APIs are JSON-safe, analysis-only, and readiness monitored", False, str(exc))
        return False


def main() -> int:
    print("Phase 2 Day 9 Session and Killzone Intelligence Verification")
    print("=" * 60)
    checks = [
        verify_path("backend/institutional_intelligence/session_models.py", "session_models.py exists"),
        verify_path("backend/institutional_intelligence/session_range_detector.py", "session_range_detector.py exists"),
        verify_path("backend/institutional_intelligence/killzone_detector.py", "killzone_detector.py exists"),
        verify_path("backend/institutional_intelligence/session_liquidity_analyzer.py", "session_liquidity_analyzer.py exists"),
        verify_path("backend/institutional_intelligence/session_manipulation_detector.py", "session_manipulation_detector.py exists"),
        verify_path("backend/institutional_intelligence/session_quality_scorer.py", "session_quality_scorer.py exists"),
        verify_path("backend/institutional_intelligence/session_context_builder.py", "session_context_builder.py exists"),
        verify_routes(),
        verify_ranges_and_killzones(),
        verify_manipulation_and_quality(),
        verify_news_and_alignment_guards(),
        verify_malformed_and_service_fallback(),
        verify_api_json_and_health(),
    ]
    print("=" * 60)
    passed = all(checks)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
