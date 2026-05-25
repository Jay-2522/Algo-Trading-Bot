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
        "time": datetime(2026, 1, 5, tzinfo=timezone.utc) + timedelta(minutes=index * 15),
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
    }


def bullish_breaker_pattern() -> list[dict]:
    return [
        candle(0, 110.0, 111.0, 109.0, 109.8),
        candle(1, 109.8, 111.0, 109.0, 110.0),
        candle(2, 110.0, 111.2, 109.8, 111.0),
        candle(3, 111.0, 111.1, 105.0, 105.5),
        candle(4, 105.5, 106.0, 104.8, 105.2),
        candle(5, 105.2, 113.0, 105.0, 112.5),
    ]


def bearish_breaker_pattern() -> list[dict]:
    return [
        candle(0, 100.0, 101.0, 99.0, 100.2),
        candle(1, 100.2, 101.0, 99.0, 100.0),
        candle(2, 100.0, 100.5, 98.8, 99.0),
        candle(3, 99.0, 104.0, 98.9, 103.5),
        candle(4, 103.5, 104.0, 103.0, 103.8),
        candle(5, 103.8, 104.0, 97.0, 97.5),
    ]


def source_context(candles: list[dict]):
    from backend.institutional_intelligence.smc_service import SMCService

    return SMCService().analyze_order_blocks_from_candles("XAUUSD", "M15", candles)


def verify_routes() -> bool:
    try:
        from backend.main import app

        paths = {route.path for route in app.routes}
        required = {
            "/system/status",
            "/institutional/status",
            "/institutional/fvg/{symbol}",
            "/institutional/order-blocks/{symbol}",
            "/institutional/order-blocks/context/{symbol}",
            "/institutional/breakers/{symbol}",
            "/institutional/breakers/fresh/{symbol}",
            "/institutional/breakers/mitigated/{symbol}",
            "/institutional/breakers/high-quality/{symbol}",
            "/institutional/breakers/latest/{symbol}",
            "/institutional/breakers/context/{symbol}",
        }
        missing = sorted(required - paths)
        passed = not missing
        print_result("Breaker, prior institutional, and Phase 1 routes remain registered", passed, str(missing))
        return passed
    except Exception as exc:
        print_result("FastAPI app imports with breaker block routes", False, str(exc))
        return False


def verify_detector_and_validator() -> bool:
    try:
        from backend.institutional_intelligence.breaker_block_detector import BreakerBlockDetector
        from backend.institutional_intelligence.breaker_block_validator import BreakerBlockValidator

        bullish_candles = bullish_breaker_pattern()
        bearish_candles = bearish_breaker_pattern()
        bullish_ob_context = source_context(bullish_candles)
        bearish_ob_context = source_context(bearish_candles)
        detector = BreakerBlockDetector()
        bullish = detector.detect_breaker_blocks(
            bullish_candles, bullish_ob_context.order_blocks, "XAUUSD", "M15"
        )
        bearish = detector.detect_breaker_blocks(
            bearish_candles, bearish_ob_context.order_blocks, "XAUUSD", "M15"
        )
        bullish_source = next(ob for ob in bullish_ob_context.order_blocks if ob.ob_id == bullish[0].source_order_block_id)
        bearish_source = next(ob for ob in bearish_ob_context.order_blocks if ob.ob_id == bearish[0].source_order_block_id)
        bullish_valid = BreakerBlockValidator().validate_breaker_block(bullish[0], bullish_candles, bullish_source)
        bearish_valid = BreakerBlockValidator().validate_breaker_block(bearish[0], bearish_candles, bearish_source)
        passed = (
            len(bullish) == 1
            and bullish[0].direction == "BULLISH"
            and bullish[0].original_ob_direction == "BEARISH"
            and len(bearish) == 1
            and bearish[0].direction == "BEARISH"
            and bearish[0].original_ob_direction == "BULLISH"
            and bullish_valid.valid
            and bearish_valid.valid
            and bullish[0].source_order_block_id == bullish_source.ob_id
            and detector.detect_breaker_blocks([{"bad": True}], [], "XAUUSD", "M15") == []
        )
        print_result("Detector transforms failed valid OBs into directional, source-linked breakers", passed)
        return passed
    except Exception as exc:
        print_result("Detector transforms failed valid OBs into directional, source-linked breakers", False, str(exc))
        return False


def verify_mitigation() -> bool:
    try:
        from backend.institutional_intelligence.breaker_block_detector import BreakerBlockDetector
        from backend.institutional_intelligence.breaker_block_mitigation_tracker import BreakerBlockMitigationTracker

        candles = bullish_breaker_pattern()
        breaker = BreakerBlockDetector().detect_breaker_blocks(
            candles, source_context(candles).order_blocks, "XAUUSD", "M15"
        )[0]
        tracker = BreakerBlockMitigationTracker()
        partial = tracker.evaluate_mitigation(breaker, [candle(6, 113.0, 114.0, 110.5, 112.0)])
        full = tracker.evaluate_mitigation(breaker, [candle(6, 113.0, 114.0, 109.0, 110.0)])
        passed = (
            partial.status == "PARTIALLY_MITIGATED"
            and partial.touched
            and 0 < partial.mitigation_percent < 100
            and full.status == "MITIGATED"
            and full.fully_mitigated
            and full.mitigation_percent == 100.0
        )
        print_result("Breaker lifecycle tracks partial and full zone mitigation", passed)
        return passed
    except Exception as exc:
        print_result("Breaker lifecycle tracks partial and full zone mitigation", False, str(exc))
        return False


def verify_scoring_and_context() -> bool:
    try:
        from backend.institutional_intelligence.breaker_block_context_builder import BreakerBlockContextBuilder
        from backend.institutional_intelligence.breaker_block_detector import BreakerBlockDetector
        from backend.institutional_intelligence.breaker_block_models import BreakerBlockContext
        from backend.institutional_intelligence.breaker_block_strength_scorer import BreakerBlockStrengthScorer
        from backend.institutional_intelligence.smc_models import StructureBias

        candles = bullish_breaker_pattern()
        order_blocks = source_context(candles)
        breaker = BreakerBlockDetector().detect_breaker_blocks(candles, order_blocks.order_blocks, "XAUUSD", "M15")[0]
        confirmed = breaker.model_copy(update={"valid": True})
        fvg_context = {"fresh_fvgs": [{"direction": "BULLISH", "start_index": 5, "fvg_id": "FVG-BRK"}]}
        sweep_context = {
            "sweeps": [{"direction": "BULLISH", "candle_index": 4, "valid": True, "sweep_id": "SWP-BRK"}]
        }
        bias = StructureBias(bias="BULLISH", confidence=80)
        score = BreakerBlockStrengthScorer().score_breaker_block(
            confirmed, fvg_context=fvg_context, sweep_context=sweep_context, structure_bias=bias
        )
        context = BreakerBlockContextBuilder().build_breaker_context(
            "XAUUSD",
            "M15",
            candles,
            order_block_context=order_blocks,
            fvg_context=fvg_context,
            sweep_context=sweep_context,
            structure_bias=bias,
        )
        passed = (
            isinstance(context, BreakerBlockContext)
            and len(context.breaker_blocks) == 1
            and context.latest_breaker is not None
            and bool(context.fresh_breakers)
            and bool(context.high_quality_breakers)
            and 0 <= score.score <= 100
            and score.confluence_score == 15.0
            and context.confidence > 0
        )
        print_result("Breaker context and deterministic confluence scoring are bounded and typed", passed)
        return passed
    except Exception as exc:
        print_result("Breaker context and deterministic confluence scoring are bounded and typed", False, str(exc))
        return False


def verify_service_fallback() -> bool:
    try:
        from backend.institutional_intelligence.smc_service import SMCService

        class UnavailableData:
            def get_candles(self, *args, **kwargs):
                raise RuntimeError("No MT5 needed for breaker verification.")

            def close(self):
                return None

        context = SMCService(market_data_service=UnavailableData()).analyze_breaker_blocks("XAUUSD")
        passed = context.symbol == "XAUUSD" and context.breaker_blocks == [] and context.latest_breaker is None
        print_result("SMCService safely returns empty breaker context without MT5", passed)
        return passed
    except Exception as exc:
        print_result("SMCService safely returns empty breaker context without MT5", False, str(exc))
        return False


def verify_api_json_and_health() -> bool:
    try:
        from backend.api import institutional_routes
        from backend.institutional_intelligence.smc_service import SMCService
        from backend.main import app

        class UnavailableData:
            def get_candles(self, *args, **kwargs):
                raise RuntimeError("API JSON verification does not require MT5.")

            def close(self):
                return None

        client = TestClient(app)
        service = institutional_routes.smc_service
        institutional_routes.smc_service = SMCService(market_data_service=UnavailableData())
        try:
            endpoints = [
                "/institutional/breakers/XAUUSD",
                "/institutional/breakers/fresh/XAUUSD",
                "/institutional/breakers/mitigated/XAUUSD",
                "/institutional/breakers/high-quality/XAUUSD",
                "/institutional/breakers/latest/XAUUSD",
                "/institutional/breakers/context/XAUUSD",
            ]
            responses = [client.get(endpoint) for endpoint in endpoints]
            readiness = client.get("/system/readiness")
        finally:
            institutional_routes.smc_service = service
        context_json = responses[0].json()
        combined_json = responses[-1].json()
        passed = (
            all(response.status_code == 200 for response in responses)
            and "breaker_blocks" in context_json
            and all(isinstance(response.json(), list) for response in responses[1:4])
            and "order_blocks" in combined_json
            and "fair_value_gaps" in combined_json
            and combined_json["simulation_only"] is True
            and combined_json["live_execution_enabled"] is False
            and any(module["module_name"] == "institutional_breaker_blocks" for module in readiness.json()["modules"])
        )
        print_result("Breaker APIs are JSON-safe, analysis-only, and readiness monitored", passed)
        return passed
    except Exception as exc:
        print_result("Breaker APIs are JSON-safe, analysis-only, and readiness monitored", False, str(exc))
        return False


def main() -> int:
    print("Phase 2 Day 5 Breaker Block Detection Verification")
    print("=" * 50)
    checks = [
        verify_path("backend/institutional_intelligence/breaker_block_models.py", "breaker_block_models.py exists"),
        verify_path("backend/institutional_intelligence/breaker_block_detector.py", "breaker_block_detector.py exists"),
        verify_path("backend/institutional_intelligence/breaker_block_validator.py", "breaker_block_validator.py exists"),
        verify_path(
            "backend/institutional_intelligence/breaker_block_mitigation_tracker.py",
            "breaker_block_mitigation_tracker.py exists",
        ),
        verify_path(
            "backend/institutional_intelligence/breaker_block_strength_scorer.py",
            "breaker_block_strength_scorer.py exists",
        ),
        verify_path(
            "backend/institutional_intelligence/breaker_block_context_builder.py",
            "breaker_block_context_builder.py exists",
        ),
        verify_routes(),
        verify_detector_and_validator(),
        verify_mitigation(),
        verify_scoring_and_context(),
        verify_service_fallback(),
        verify_api_json_and_health(),
    ]
    print("=" * 50)
    passed = all(checks)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
