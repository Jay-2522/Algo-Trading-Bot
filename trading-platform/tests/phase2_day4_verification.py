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
        "time": datetime(2026, 1, 4, tzinfo=timezone.utc) + timedelta(minutes=index * 15),
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
    }


def bullish_pattern() -> list[dict]:
    return [
        candle(0, 100.0, 101.0, 99.0, 100.2),
        candle(1, 100.2, 101.0, 99.0, 100.0),
        candle(2, 100.0, 100.5, 98.8, 99.0),
        candle(3, 99.0, 104.0, 98.9, 103.5),
    ]


def bearish_pattern() -> list[dict]:
    return [
        candle(0, 110.0, 111.0, 109.0, 109.8),
        candle(1, 109.8, 111.0, 109.0, 110.0),
        candle(2, 110.0, 111.2, 109.8, 111.0),
        candle(3, 111.0, 111.1, 105.0, 105.5),
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
            "/institutional/fvg/{symbol}",
            "/institutional/fvg/fresh/{symbol}",
            "/institutional/fvg/latest/{symbol}",
            "/institutional/order-blocks/{symbol}",
            "/institutional/order-blocks/fresh/{symbol}",
            "/institutional/order-blocks/mitigated/{symbol}",
            "/institutional/order-blocks/high-quality/{symbol}",
            "/institutional/order-blocks/latest/{symbol}",
            "/institutional/order-blocks/context/{symbol}",
        }
        missing = sorted(required - paths)
        passed = not missing
        print_result("Order block, previous institutional, and Phase 1 routes remain registered", passed, str(missing))
        return passed
    except Exception as exc:
        print_result("FastAPI app imports with order block routes", False, str(exc))
        return False


def verify_detector_and_validator() -> bool:
    try:
        from backend.institutional_intelligence.order_block_detector import OrderBlockDetector
        from backend.institutional_intelligence.order_block_validator import OrderBlockValidator

        detector = OrderBlockDetector()
        bullish = detector.detect_bullish_order_block(bullish_pattern(), 2, "XAUUSD", "M15")
        bearish = detector.detect_bearish_order_block(bearish_pattern(), 2, "XAUUSD", "M15")
        consecutive_down_candles = [
            candle(0, 100.0, 101.0, 99.0, 100.2),
            candle(1, 100.2, 101.0, 99.0, 100.0),
            candle(2, 100.0, 100.5, 98.8, 99.4),
            candle(3, 99.4, 99.8, 98.5, 98.9),
            candle(4, 99.0, 104.0, 98.8, 103.5),
        ]
        latest_origin = detector.detect_order_blocks(consecutive_down_candles, "XAUUSD", "M15")
        bullish_validation = OrderBlockValidator().validate_order_block(bullish, bullish_pattern())
        bearish_validation = OrderBlockValidator().validate_order_block(bearish, bearish_pattern())
        passed = (
            bullish is not None
            and bullish.direction == "BULLISH"
            and bearish is not None
            and bearish.direction == "BEARISH"
            and bullish_validation.valid
            and bullish_validation.displacement_confirmed
            and bullish_validation.bos_confirmed
            and bearish_validation.valid
            and bearish_validation.bos_confirmed
            and [order_block.candle_index for order_block in latest_origin] == [3]
            and detector.detect_order_blocks([{"bad": float("nan")}], "XAUUSD", "M15") == []
        )
        print_result("Detector identifies directional OBs and validator confirms displacement plus BOS", passed)
        return passed
    except Exception as exc:
        print_result("Detector identifies directional OBs and validator confirms displacement plus BOS", False, str(exc))
        return False


def verify_mitigation() -> bool:
    try:
        from backend.institutional_intelligence.order_block_detector import OrderBlockDetector
        from backend.institutional_intelligence.order_block_mitigation_tracker import OrderBlockMitigationTracker

        order_block = OrderBlockDetector().detect_bullish_order_block(bullish_pattern(), 2, "XAUUSD", "M15")
        tracker = OrderBlockMitigationTracker()
        partial = tracker.evaluate_mitigation(order_block, [candle(4, 101.0, 102.0, 99.6, 101.0)])
        full = tracker.evaluate_mitigation(order_block, [candle(4, 101.0, 102.0, 98.0, 99.0)])
        passed = (
            partial.status == "PARTIAL"
            and partial.touched
            and 0 < partial.mitigation_percent < 100
            and full.status == "MITIGATED"
            and full.fully_mitigated
            and full.mitigation_percent == 100.0
        )
        print_result("Mitigation tracker distinguishes partial and fully mitigated order blocks", passed)
        return passed
    except Exception as exc:
        print_result("Mitigation tracker distinguishes partial and fully mitigated order blocks", False, str(exc))
        return False


def verify_scoring_and_context() -> bool:
    try:
        from backend.institutional_intelligence.order_block_context_builder import OrderBlockContextBuilder
        from backend.institutional_intelligence.order_block_detector import OrderBlockDetector
        from backend.institutional_intelligence.order_block_models import OrderBlockContext
        from backend.institutional_intelligence.order_block_strength_scorer import OrderBlockStrengthScorer
        from backend.institutional_intelligence.order_block_validator import OrderBlockValidator
        from backend.institutional_intelligence.smc_models import StructureBias

        order_block = OrderBlockDetector().detect_bullish_order_block(bullish_pattern(), 2, "XAUUSD", "M15")
        validation = OrderBlockValidator().validate_order_block(order_block, bullish_pattern())
        confirmed = order_block.model_copy(update={"valid": validation.valid, "bos_confirmed": validation.bos_confirmed})
        score = OrderBlockStrengthScorer().score_order_block(
            confirmed,
            bullish_pattern(),
            fvg_context={"fresh_fvgs": [{"direction": "BULLISH", "start_index": 3, "fvg_id": "FVG-TEST"}]},
            sweep_context={"sweeps": [{"direction": "BULLISH", "candle_index": 2, "valid": True, "sweep_id": "SWP-TEST"}]},
            structure_bias=StructureBias(bias="BULLISH", confidence=80),
        )
        context = OrderBlockContextBuilder().build_order_block_context(
            "XAUUSD",
            "M15",
            bullish_pattern(),
            structure_bias=StructureBias(bias="BULLISH", confidence=80),
        )
        passed = (
            isinstance(context, OrderBlockContext)
            and bool(context.order_blocks)
            and context.latest_order_block is not None
            and bool(context.fresh_order_blocks)
            and 0 <= score.score <= 100
            and score.confluence_score == 15.0
            and context.confidence > 0
        )
        print_result("Typed context and deterministic bounded confluence scoring are available", passed)
        return passed
    except Exception as exc:
        print_result("Typed context and deterministic bounded confluence scoring are available", False, str(exc))
        return False


def verify_service_fallback() -> bool:
    try:
        from backend.institutional_intelligence.smc_service import SMCService

        class UnavailableData:
            def get_candles(self, *args, **kwargs):
                raise RuntimeError("No MT5 needed for order block verification.")

            def close(self):
                return None

        context = SMCService(market_data_service=UnavailableData()).analyze_order_blocks("XAUUSD")
        passed = context.symbol == "XAUUSD" and context.order_blocks == [] and context.latest_order_block is None
        print_result("SMCService safely returns empty order block context without MT5", passed)
        return passed
    except Exception as exc:
        print_result("SMCService safely returns empty order block context without MT5", False, str(exc))
        return False


def verify_api_json_and_health() -> bool:
    try:
        from backend.main import app
        from backend.api import institutional_routes
        from backend.institutional_intelligence.smc_service import SMCService

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
                "/institutional/order-blocks/XAUUSD",
                "/institutional/order-blocks/fresh/XAUUSD",
                "/institutional/order-blocks/mitigated/XAUUSD",
                "/institutional/order-blocks/high-quality/XAUUSD",
                "/institutional/order-blocks/latest/XAUUSD",
                "/institutional/order-blocks/context/XAUUSD",
            ]
            responses = [client.get(endpoint) for endpoint in endpoints]
            readiness = client.get("/system/readiness")
        finally:
            institutional_routes.smc_service = service
        context_json = responses[0].json()
        combined_json = responses[-1].json()
        passed = (
            all(response.status_code == 200 for response in responses)
            and "order_blocks" in context_json
            and isinstance(responses[1].json(), list)
            and "fair_value_gaps" in combined_json
            and combined_json["simulation_only"] is True
            and combined_json["live_execution_enabled"] is False
            and any(module["module_name"] == "institutional_order_blocks" for module in readiness.json()["modules"])
        )
        print_result("Order block APIs are JSON-safe, analysis-only, and readiness monitored", passed)
        return passed
    except Exception as exc:
        print_result("Order block APIs are JSON-safe, analysis-only, and readiness monitored", False, str(exc))
        return False


def main() -> int:
    print("Phase 2 Day 4 Order Block Detection Verification")
    print("=" * 48)
    checks = [
        verify_path("backend/institutional_intelligence/order_block_models.py", "order_block_models.py exists"),
        verify_path("backend/institutional_intelligence/order_block_detector.py", "order_block_detector.py exists"),
        verify_path("backend/institutional_intelligence/order_block_validator.py", "order_block_validator.py exists"),
        verify_path("backend/institutional_intelligence/order_block_mitigation_tracker.py", "order_block_mitigation_tracker.py exists"),
        verify_path("backend/institutional_intelligence/order_block_strength_scorer.py", "order_block_strength_scorer.py exists"),
        verify_path("backend/institutional_intelligence/order_block_context_builder.py", "order_block_context_builder.py exists"),
        verify_routes(),
        verify_detector_and_validator(),
        verify_mitigation(),
        verify_scoring_and_context(),
        verify_service_fallback(),
        verify_api_json_and_health(),
    ]
    print("=" * 48)
    passed = all(checks)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
