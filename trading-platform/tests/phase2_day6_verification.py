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
        "time": datetime(2026, 1, 6, tzinfo=timezone.utc) + timedelta(minutes=index * 15),
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
    }


def bullish_shift_candles() -> list[dict]:
    return [
        candle(0, 104.0, 105.0, 103.0, 104.0),
        candle(1, 103.0, 104.0, 101.0, 102.0),
        candle(2, 104.0, 105.0, 102.0, 103.0),
        candle(3, 101.0, 102.0, 99.0, 100.0),
        candle(4, 101.0, 103.0, 100.0, 102.0),
        candle(5, 102.0, 109.0, 101.0, 108.0),
        candle(6, 108.0, 110.0, 107.0, 109.0),
    ]


def bearish_shift_candles() -> list[dict]:
    return [
        candle(0, 100.0, 101.0, 99.0, 100.0),
        candle(1, 101.0, 103.0, 100.0, 102.0),
        candle(2, 100.0, 102.0, 99.0, 101.0),
        candle(3, 102.0, 104.0, 101.0, 103.0),
        candle(4, 101.0, 103.0, 100.0, 101.0),
        candle(5, 101.0, 102.0, 94.0, 95.0),
        candle(6, 95.0, 96.0, 93.0, 94.0),
    ]


def bullish_swings():
    from backend.institutional_intelligence.smc_models import SwingPoint

    candles = bullish_shift_candles()
    return [
        SwingPoint(index=2, timestamp=candles[2]["time"], price=105.0, type="HIGH", strength=2.0),
        SwingPoint(index=3, timestamp=candles[3]["time"], price=99.0, type="LOW", strength=2.0),
        SwingPoint(index=4, timestamp=candles[4]["time"], price=103.0, type="HIGH", strength=2.0),
    ]


def bearish_swings():
    from backend.institutional_intelligence.smc_models import SwingPoint

    candles = bearish_shift_candles()
    return [
        SwingPoint(index=2, timestamp=candles[2]["time"], price=99.0, type="LOW", strength=2.0),
        SwingPoint(index=3, timestamp=candles[3]["time"], price=104.0, type="HIGH", strength=2.0),
        SwingPoint(index=4, timestamp=candles[4]["time"], price=100.0, type="LOW", strength=2.0),
    ]


def verify_routes() -> bool:
    try:
        from backend.main import app

        paths = {route.path for route in app.routes}
        required = {
            "/system/status",
            "/institutional/status",
            "/institutional/order-blocks/{symbol}",
            "/institutional/breakers/{symbol}",
            "/institutional/structure-shift/{symbol}",
            "/institutional/structure-shift/bos/{symbol}",
            "/institutional/structure-shift/choch/{symbol}",
            "/institutional/structure-shift/mss/{symbol}",
            "/institutional/structure-shift/latest/{symbol}",
            "/institutional/structure-shift/high-quality/{symbol}",
            "/institutional/structure-shift/context/{symbol}",
        }
        missing = sorted(required - paths)
        passed = not missing
        print_result("Structure shift, prior institutional, and Phase 1 routes remain registered", passed, str(missing))
        return passed
    except Exception as exc:
        print_result("FastAPI app imports with structure shift routes", False, str(exc))
        return False


def verify_bos_and_weak_break() -> bool:
    try:
        from backend.institutional_intelligence.bos_detector import BOSDetector
        from backend.institutional_intelligence.smc_models import SwingPoint

        bullish = BOSDetector().detect_bos(bullish_shift_candles(), bullish_swings(), "XAUUSD", "M15")
        weak_candles = [
            candle(0, 100, 101, 99, 100),
            candle(1, 101, 102, 100, 101),
            candle(2, 102, 105, 101, 103),
            candle(3, 103, 106, 102, 104),
        ]
        swing = SwingPoint(index=2, timestamp=weak_candles[2]["time"], price=105, type="HIGH", strength=1)
        weak = BOSDetector().detect_bos(weak_candles, [swing], "XAUUSD", "M15")
        passed = (
            any(event.direction == "BULLISH" and event.close_confirmed for event in bullish)
            and len(weak) == 1
            and weak[0].wick_break
            and not weak[0].close_confirmed
            and BOSDetector().detect_bos([{"bad": True}], [], "XAUUSD", "M15") == []
        )
        print_result("BOS detects close-confirmed breaks and distinguishes wick-only weak breaks", passed)
        return passed
    except Exception as exc:
        print_result("BOS detects close-confirmed breaks and distinguishes wick-only weak breaks", False, str(exc))
        return False


def verify_choch_mss_and_validation() -> bool:
    try:
        from backend.institutional_intelligence.smc_models import StructureBias
        from backend.institutional_intelligence.structure_shift_detector import StructureShiftDetector
        from backend.institutional_intelligence.structure_shift_validator import StructureShiftValidator

        detector = StructureShiftDetector()
        bullish = detector.detect_structure_events(
            bullish_shift_candles(), bullish_swings(), "XAUUSD", "M15", StructureBias(bias="BEARISH")
        )
        bearish = detector.detect_structure_events(
            bearish_shift_candles(), bearish_swings(), "XAUUSD", "M15", StructureBias(bias="BULLISH")
        )
        bullish_mss = next(event for event in bullish if event.event_type == "MSS")
        bearish_mss = next(event for event in bearish if event.event_type == "MSS")
        validation = StructureShiftValidator().validate_event(bullish_mss, bullish_shift_candles(), bullish_swings())
        passed = (
            any(event.event_type == "CHOCH" and event.direction == "BULLISH" for event in bullish)
            and bullish_mss.direction == "BULLISH"
            and any(event.event_type == "CHOCH" and event.direction == "BEARISH" for event in bearish)
            and bearish_mss.direction == "BEARISH"
            and validation.valid
            and validation.close_confirmed
            and bullish_mss.metadata["mss_confirmation"] == "CHOCH_WITH_DISPLACEMENT"
        )
        print_result("CHOCH detects counter-bias reversals and MSS requires confirmation", passed)
        return passed
    except Exception as exc:
        print_result("CHOCH detects counter-bias reversals and MSS requires confirmation", False, str(exc))
        return False


def verify_scoring_and_context() -> bool:
    try:
        from backend.institutional_intelligence.smc_models import StructureBias
        from backend.institutional_intelligence.structure_shift_context_builder import StructureShiftContextBuilder
        from backend.institutional_intelligence.structure_shift_strength_scorer import StructureShiftStrengthScorer

        bias = StructureBias(bias="BULLISH", confidence=80)
        raw = StructureShiftContextBuilder().detector.detect_structure_events(
            bullish_shift_candles(), bullish_swings(), "XAUUSD", "M15", StructureBias(bias="BEARISH")
        )
        event = next(item for item in raw if item.event_type == "MSS").model_copy(update={"valid": True})
        sweeps = {"sweeps": [{"valid": True, "direction": "BULLISH", "swept_level": 103.0, "candle_index": 5, "sweep_id": "SWP-STR"}]}
        fvgs = {"fresh_fvgs": [{"direction": "BULLISH", "start_index": 5, "fvg_id": "FVG-STR"}]}
        obs = {"order_blocks": [{"valid": True, "direction": "BULLISH", "candle_index": 4, "ob_id": "OB-STR"}]}
        breakers = {"breaker_blocks": [{"valid": True, "direction": "BULLISH", "candle_index": 5, "breaker_id": "BRK-STR"}]}
        score = StructureShiftStrengthScorer().score_event(
            event, bullish_shift_candles(), bullish_swings(), sweeps, fvgs, obs, breakers, bias
        )
        context = StructureShiftContextBuilder().build_structure_shift_context(
            "XAUUSD", "M15", bullish_shift_candles(), bullish_swings(), sweeps, fvgs, obs, breakers, StructureBias(bias="BEARISH")
        )
        inferred = StructureShiftContextBuilder().build_structure_shift_context(
            "XAUUSD", "M15", bullish_shift_candles(), bullish_swings()
        )
        passed = (
            bool(context.bos_events)
            and bool(context.choch_events)
            and bool(context.mss_events)
            and context.latest_event is not None
            and context.current_structure_state == "BULLISH"
            and 0 <= score.score <= 100
            and score.confluence_score == 20.0
            and context.confidence > 0
            and bool(inferred.choch_events)
            and bool(inferred.mss_events)
        )
        print_result("Structure context classifies events and deterministic confluence is bounded", passed)
        return passed
    except Exception as exc:
        print_result("Structure context classifies events and deterministic confluence is bounded", False, str(exc))
        return False


def verify_service_fallback() -> bool:
    try:
        from backend.institutional_intelligence.smc_service import SMCService

        class UnavailableData:
            def get_candles(self, *args, **kwargs):
                raise RuntimeError("No MT5 needed for structure shift verification.")

            def close(self):
                return None

        context = SMCService(market_data_service=UnavailableData()).analyze_structure_shift("XAUUSD")
        passed = context.symbol == "XAUUSD" and context.events == [] and context.latest_event is None
        print_result("SMCService safely returns empty structure shift context without MT5", passed)
        return passed
    except Exception as exc:
        print_result("SMCService safely returns empty structure shift context without MT5", False, str(exc))
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
                "/institutional/structure-shift/XAUUSD",
                "/institutional/structure-shift/bos/XAUUSD",
                "/institutional/structure-shift/choch/XAUUSD",
                "/institutional/structure-shift/mss/XAUUSD",
                "/institutional/structure-shift/latest/XAUUSD",
                "/institutional/structure-shift/high-quality/XAUUSD",
                "/institutional/structure-shift/context/XAUUSD",
            ]
            responses = [client.get(endpoint) for endpoint in endpoints]
            readiness = client.get("/system/readiness")
        finally:
            institutional_routes.smc_service = service
        combined = responses[-1].json()
        passed = (
            all(response.status_code == 200 for response in responses)
            and "events" in responses[0].json()
            and all(isinstance(response.json(), list) for response in responses[1:4])
            and "breaker_blocks" in combined
            and combined["simulation_only"] is True
            and combined["live_execution_enabled"] is False
            and any(module["module_name"] == "institutional_structure_shift" for module in readiness.json()["modules"])
        )
        print_result("Structure shift APIs are JSON-safe, analysis-only, and readiness monitored", passed)
        return passed
    except Exception as exc:
        print_result("Structure shift APIs are JSON-safe, analysis-only, and readiness monitored", False, str(exc))
        return False


def main() -> int:
    print("Phase 2 Day 6 Market Structure Shift Verification")
    print("=" * 49)
    checks = [
        verify_path("backend/institutional_intelligence/structure_shift_models.py", "structure_shift_models.py exists"),
        verify_path("backend/institutional_intelligence/structure_shift_detector.py", "structure_shift_detector.py exists"),
        verify_path("backend/institutional_intelligence/bos_detector.py", "bos_detector.py exists"),
        verify_path("backend/institutional_intelligence/choch_detector.py", "choch_detector.py exists"),
        verify_path("backend/institutional_intelligence/structure_shift_validator.py", "structure_shift_validator.py exists"),
        verify_path("backend/institutional_intelligence/structure_shift_strength_scorer.py", "structure_shift_strength_scorer.py exists"),
        verify_path("backend/institutional_intelligence/structure_shift_context_builder.py", "structure_shift_context_builder.py exists"),
        verify_routes(),
        verify_bos_and_weak_break(),
        verify_choch_mss_and_validation(),
        verify_scoring_and_context(),
        verify_service_fallback(),
        verify_api_json_and_health(),
    ]
    print("=" * 49)
    passed = all(checks)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
