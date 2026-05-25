import sys
from datetime import datetime, timedelta, timezone
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


def candle(index: int, open_price: float, high: float, low: float, close: float) -> dict:
    return {
        "symbol": "XAUUSD",
        "timeframe": "M15",
        "time": datetime(2026, 1, 3, tzinfo=timezone.utc) + timedelta(minutes=index * 15),
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
    }


def bullish_pattern() -> list[dict]:
    return [
        candle(0, 99, 100, 98, 99),
        candle(1, 100, 108, 100, 107),
        candle(2, 105, 109, 103, 108),
    ]


def bearish_pattern() -> list[dict]:
    return [
        candle(0, 111, 113, 110, 112),
        candle(1, 110, 110, 102, 103),
        candle(2, 105, 107, 101, 102),
    ]


def verify_routes() -> bool:
    try:
        from backend.main import app

        paths = {route.path for route in app.routes}
        required = {
            "/system/status",
            "/institutional/status",
            "/institutional/sweeps/{symbol}",
            "/institutional/fvg/{symbol}",
            "/institutional/fvg/fresh/{symbol}",
            "/institutional/fvg/mitigated/{symbol}",
            "/institutional/fvg/high-quality/{symbol}",
            "/institutional/fvg/latest/{symbol}",
        }
        missing = sorted(required - paths)
        passed = not missing
        print_result("FVG routes registered while prior institutional and Phase 1 routes remain", passed, str(missing))
        return passed
    except Exception as exc:
        print_result("FVG routes registered while prior institutional and Phase 1 routes remain", False, str(exc))
        return False


def verify_detector() -> bool:
    try:
        from backend.institutional_intelligence.fair_value_gap_detector import FairValueGapDetector

        detector = FairValueGapDetector()
        bullish = detector.detect_bullish_fvg(bullish_pattern(), 1, "XAUUSD", "M15")
        bearish = detector.detect_bearish_fvg(bearish_pattern(), 1, "XAUUSD", "M15")
        passed = (
            bullish is not None
            and bullish.direction == "BULLISH"
            and bullish.gap_low == 100.0
            and bullish.gap_high == 103.0
            and bearish is not None
            and bearish.direction == "BEARISH"
            and bearish.gap_low == 107.0
            and bearish.gap_high == 110.0
            and detector.detect_fvgs([{"bad": True}], "XAUUSD", "M15") == []
        )
        print_result("Detector identifies bullish and bearish three-candle imbalances safely", passed)
        return passed
    except Exception as exc:
        print_result("Detector identifies bullish and bearish three-candle imbalances safely", False, str(exc))
        return False


def verify_mitigation() -> bool:
    try:
        from backend.institutional_intelligence.fair_value_gap_detector import FairValueGapDetector
        from backend.institutional_intelligence.fvg_mitigation_tracker import FVGMitigationTracker

        fvg = FairValueGapDetector().detect_bullish_fvg(bullish_pattern(), 1, "XAUUSD", "M15")
        tracker = FVGMitigationTracker()
        partial = tracker.evaluate_mitigation(fvg, [candle(3, 104, 106, 102, 104)])
        full = tracker.evaluate_mitigation(fvg, [candle(3, 104, 106, 99, 101)])
        passed = (
            partial.status == "PARTIAL"
            and 0 < partial.mitigation_percent < 100
            and full.status == "MITIGATED"
            and full.fully_mitigated
            and full.mitigation_percent == 100.0
        )
        print_result("Mitigation tracker distinguishes partial and full fills", passed)
        return passed
    except Exception as exc:
        print_result("Mitigation tracker distinguishes partial and full fills", False, str(exc))
        return False


def verify_scoring_and_context() -> bool:
    try:
        from backend.institutional_intelligence.fair_value_gap_detector import FairValueGapDetector
        from backend.institutional_intelligence.fvg_context_builder import FVGContextBuilder
        from backend.institutional_intelligence.fvg_mitigation_tracker import FVGMitigationTracker
        from backend.institutional_intelligence.fvg_strength_scorer import FVGStrengthScorer
        from backend.institutional_intelligence.smc_models import StructureBias

        fvg = FairValueGapDetector().detect_bullish_fvg(bullish_pattern(), 1, "XAUUSD", "M15")
        partial = FVGMitigationTracker().update_fvg_mitigation(fvg, [candle(3, 104, 106, 102, 104)])
        fresh_score = FVGStrengthScorer().score_fvg(
            fvg,
            bullish_pattern(),
            StructureBias(bias="BULLISH", confidence=80),
        )
        partial_score = FVGStrengthScorer().score_fvg(
            partial,
            bullish_pattern(),
            StructureBias(bias="BULLISH", confidence=80),
        )
        context = FVGContextBuilder().build_fvg_context("XAUUSD", "M15", bullish_pattern())
        passed = (
            0 <= fresh_score.score <= 100
            and fresh_score.score > partial_score.score
            and context.latest_fvg is not None
            and bool(context.fresh_fvgs)
            and bool(context.bullish_fvgs)
            and "bias_aligned" in context.latest_fvg.metadata
        )
        print_result("FVG scoring is bounded, freshness-sensitive, and context is typed", passed)
        return passed
    except Exception as exc:
        print_result("FVG scoring is bounded, freshness-sensitive, and context is typed", False, str(exc))
        return False


def verify_service_fallback() -> bool:
    try:
        from backend.institutional_intelligence.smc_service import SMCService

        class UnavailableData:
            def get_candles(self, *args, **kwargs):
                raise RuntimeError("No MT5 needed for FVG verification.")

            def close(self):
                return None

        context = SMCService(market_data_service=UnavailableData()).analyze_fvgs("XAUUSD")
        passed = context.symbol == "XAUUSD" and context.fvgs == [] and context.latest_fvg is None
        print_result("SMCService safely returns empty FVG context without MT5", passed)
        return passed
    except Exception as exc:
        print_result("SMCService safely returns empty FVG context without MT5", False, str(exc))
        return False


def verify_api_json_and_health() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        context = client.get("/institutional/fvg/XAUUSD")
        fresh = client.get("/institutional/fvg/fresh/XAUUSD")
        mitigated = client.get("/institutional/fvg/mitigated/XAUUSD")
        high_quality = client.get("/institutional/fvg/high-quality/XAUUSD")
        latest = client.get("/institutional/fvg/latest/XAUUSD")
        readiness = client.get("/system/readiness")
        passed = (
            context.status_code == 200
            and "fvgs" in context.json()
            and all(response.status_code == 200 for response in [fresh, mitigated, high_quality, latest])
            and all(isinstance(response.json(), list) for response in [fresh, mitigated, high_quality])
            and any(module["module_name"] == "institutional_fvg" for module in readiness.json()["modules"])
        )
        print_result("FVG APIs are JSON-safe and included in readiness monitoring", passed)
        return passed
    except Exception as exc:
        print_result("FVG APIs are JSON-safe and included in readiness monitoring", False, str(exc))
        return False


def main() -> int:
    print("Phase 2 Day 3 Fair Value Gap Detection Verification")
    print("=" * 51)
    checks = [
        verify_path("backend/institutional_intelligence/fair_value_gap_models.py", "fair_value_gap_models.py exists"),
        verify_path("backend/institutional_intelligence/fair_value_gap_detector.py", "fair_value_gap_detector.py exists"),
        verify_path("backend/institutional_intelligence/fvg_mitigation_tracker.py", "fvg_mitigation_tracker.py exists"),
        verify_path("backend/institutional_intelligence/fvg_strength_scorer.py", "fvg_strength_scorer.py exists"),
        verify_path("backend/institutional_intelligence/fvg_context_builder.py", "fvg_context_builder.py exists"),
        verify_routes(),
        verify_detector(),
        verify_mitigation(),
        verify_scoring_and_context(),
        verify_service_fallback(),
        verify_api_json_and_health(),
    ]
    print("=" * 51)
    passed = all(checks)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
