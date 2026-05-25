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
        "time": datetime(2026, 1, 2, tzinfo=timezone.utc) + timedelta(minutes=index * 15),
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
    }


def pools():
    from backend.institutional_intelligence.smc_models import LiquidityPool

    return [
        LiquidityPool(
            pool_id="EQH-TEST",
            symbol="XAUUSD",
            price_level=100.0,
            liquidity_type="EQUAL_HIGHS",
            strength=4.0,
            related_swings=[0],
        ),
        LiquidityPool(
            pool_id="EQL-TEST",
            symbol="XAUUSD",
            price_level=90.0,
            liquidity_type="EQUAL_LOWS",
            strength=4.0,
            related_swings=[0],
        ),
    ]


def sweep_candles() -> list[dict]:
    return [
        candle(0, 95, 99, 91, 96),
        candle(1, 99, 104, 97, 98),
        candle(2, 92, 94, 86, 92),
        candle(3, 99, 105, 98, 97),
    ]


def verify_routes() -> bool:
    try:
        from backend.main import app

        paths = {route.path for route in app.routes}
        required = {
            "/system/status",
            "/institutional/status",
            "/institutional/context/{symbol}",
            "/institutional/sweeps/{symbol}",
            "/institutional/latest-sweep/{symbol}",
            "/institutional/high-quality-sweeps/{symbol}",
        }
        missing = sorted(required - paths)
        passed = not missing
        print_result("Sweep routes registered while earlier institutional and Phase 1 routes remain", passed, str(missing))
        return passed
    except Exception as exc:
        print_result("Sweep routes registered while earlier institutional and Phase 1 routes remain", False, str(exc))
        return False


def verify_detector() -> bool:
    try:
        from backend.institutional_intelligence.liquidity_sweep_detector import LiquiditySweepDetector

        sweeps = LiquiditySweepDetector().detect_sweeps(sweep_candles(), pools(), "XAUUSD", "M15")
        passed = (
            any(sweep.sweep_type == "EQUAL_HIGH_SWEEP" and sweep.direction == "BEARISH" for sweep in sweeps)
            and any(sweep.sweep_type == "EQUAL_LOW_SWEEP" and sweep.direction == "BULLISH" for sweep in sweeps)
            and len(sweeps) == 2
            and all(sweep.close_back_inside and sweep.wick_rejection and sweep.valid for sweep in sweeps)
        )
        print_result("Detector identifies directional sweeps once per consumed liquidity pool", passed)
        return passed
    except Exception as exc:
        print_result("Detector identifies directional sweeps once per consumed liquidity pool", False, str(exc))
        return False


def verify_validator_and_scorer() -> bool:
    try:
        from backend.institutional_intelligence.sweep_strength_scorer import SweepStrengthScorer
        from backend.institutional_intelligence.sweep_validator import SweepValidator

        bearish_pool = pools()[0]
        valid = SweepValidator().validate_sweep(sweep_candles()[1], bearish_pool)
        invalid = SweepValidator().validate_sweep(candle(3, 99, 104, 98, 102), bearish_pool)
        score = SweepStrengthScorer().score_sweep(sweep_candles()[1], bearish_pool, valid)
        passed = (
            valid.valid
            and valid.close_back_inside
            and valid.wick_rejection
            and not invalid.valid
            and 0 <= score <= 100
        )
        print_result("Validator enforces rejection close and scorer remains bounded", passed)
        return passed
    except Exception as exc:
        print_result("Validator enforces rejection close and scorer remains bounded", False, str(exc))
        return False


def verify_context_builder() -> bool:
    try:
        from backend.institutional_intelligence.liquidity_sweep_models import SweepContext
        from backend.institutional_intelligence.sweep_context_builder import SweepContextBuilder

        context = SweepContextBuilder().build_sweep_context("XAUUSD", "M15", sweep_candles(), pools())
        passed = (
            isinstance(context, SweepContext)
            and len(context.sweeps) == 2
            and context.latest_sweep is not None
            and len(context.bullish_sweeps) == 1
            and len(context.bearish_sweeps) == 1
            and context.confidence > 0
            and bool(context.high_quality_sweeps)
        )
        print_result("SweepContextBuilder aggregates directional and high-quality sweeps", passed)
        return passed
    except Exception as exc:
        print_result("SweepContextBuilder aggregates directional and high-quality sweeps", False, str(exc))
        return False


def verify_service_fallback() -> bool:
    try:
        from backend.institutional_intelligence.smc_service import SMCService

        class UnavailableData:
            def get_candles(self, *args, **kwargs):
                raise RuntimeError("No MT5 needed for sweep verification.")

            def close(self):
                return None

        context = SMCService(market_data_service=UnavailableData()).analyze_liquidity_sweeps("XAUUSD")
        passed = context.symbol == "XAUUSD" and context.sweeps == [] and context.latest_sweep is None
        print_result("SMCService safely returns empty sweep context without MT5", passed)
        return passed
    except Exception as exc:
        print_result("SMCService safely returns empty sweep context without MT5", False, str(exc))
        return False


def verify_api_json() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        sweeps = client.get("/institutional/sweeps/XAUUSD")
        latest = client.get("/institutional/latest-sweep/XAUUSD")
        high_quality = client.get("/institutional/high-quality-sweeps/XAUUSD")
        readiness = client.get("/system/readiness")
        passed = (
            sweeps.status_code == 200
            and "sweeps" in sweeps.json()
            and latest.status_code == 200
            and high_quality.status_code == 200
            and isinstance(high_quality.json(), list)
            and any(
                module["module_name"] == "institutional_liquidity_sweeps"
                for module in readiness.json()["modules"]
            )
        )
        print_result("Sweep API output is JSON-safe and visible to readiness monitoring", passed)
        return passed
    except Exception as exc:
        print_result("Sweep API output is JSON-safe and visible to readiness monitoring", False, str(exc))
        return False


def main() -> int:
    print("Phase 2 Day 2 Liquidity Sweep Detection Verification")
    print("=" * 49)
    checks = [
        verify_path("backend/institutional_intelligence/liquidity_sweep_models.py", "liquidity_sweep_models.py exists"),
        verify_path("backend/institutional_intelligence/liquidity_sweep_detector.py", "liquidity_sweep_detector.py exists"),
        verify_path("backend/institutional_intelligence/sweep_validator.py", "sweep_validator.py exists"),
        verify_path("backend/institutional_intelligence/sweep_strength_scorer.py", "sweep_strength_scorer.py exists"),
        verify_path("backend/institutional_intelligence/sweep_context_builder.py", "sweep_context_builder.py exists"),
        verify_routes(),
        verify_detector(),
        verify_validator_and_scorer(),
        verify_context_builder(),
        verify_service_fallback(),
        verify_api_json(),
    ]
    print("=" * 49)
    passed = all(checks)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
