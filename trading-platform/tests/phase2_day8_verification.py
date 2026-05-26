import sys
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


def timeframe_context(direction: str, confidence: float = 90.0, event_type: str = "BOS") -> dict:
    return {
        "confluence_score": {
            "dominant_direction": direction,
            "confidence": confidence,
            "overall_score": confidence,
        },
        "institutional_context": {
            "structure_bias": {"bias": direction if direction in {"BULLISH", "BEARISH"} else "RANGING"}
        },
        "structure_shift_context": {
            "latest_event": {
                "event_type": event_type,
                "direction": direction,
            }
            if direction in {"BULLISH", "BEARISH"}
            else None
        },
    }


def verify_routes() -> bool:
    try:
        from backend.main import app

        paths = {route.path for route in app.routes}
        required = {
            "/institutional/confluence/{symbol}",
            "/institutional/alignment/{symbol}",
            "/institutional/alignment/narrative/{symbol}",
            "/institutional/alignment/conflicts/{symbol}",
            "/institutional/alignment/timeframes/{symbol}",
            "/system/readiness",
        }
        missing = sorted(required - paths)
        passed = not missing
        print_result("Alignment routes and prior protected routes remain registered", passed, str(missing))
        return passed
    except Exception as exc:
        print_result("FastAPI app imports with alignment routes", False, str(exc))
        return False


def verify_hierarchy_and_full_alignment() -> bool:
    try:
        from backend.institutional_intelligence.multi_timeframe_alignment_engine import (
            MultiTimeframeAlignmentEngine,
        )

        contexts = {
            timeframe: timeframe_context("BULLISH", 90.0, "MSS" if timeframe == "M15" else "BOS")
            for timeframe in ("H4", "H1", "M15", "M5")
        }
        alignment = MultiTimeframeAlignmentEngine().analyze_alignment("XAUUSD", contexts)
        passed = (
            alignment.macro_bias.timeframe == "H4"
            and alignment.directional_bias.timeframe == "H1"
            and alignment.execution_bias.timeframe == "M15"
            and alignment.precision_bias.timeframe == "M5"
            and alignment.overall_direction == "BULLISH"
            and alignment.alignment_quality == "FULLY_ALIGNED"
            and alignment.alignment_score == 90.0
            and alignment.confidence == 90.0
        )
        print_result("H4-to-M5 hierarchy resolves fully aligned bullish evidence", passed)
        return passed
    except Exception as exc:
        print_result("H4-to-M5 hierarchy resolves fully aligned bullish evidence", False, str(exc))
        return False


def verify_conflict_detection_and_resolution() -> bool:
    try:
        from backend.institutional_intelligence.multi_timeframe_alignment_engine import (
            MultiTimeframeAlignmentEngine,
        )

        contexts = {
            "H4": timeframe_context("BULLISH", 90.0),
            "H1": timeframe_context("BULLISH", 85.0),
            "M15": timeframe_context("BEARISH", 88.0),
            "M5": timeframe_context("BEARISH", 90.0, "MSS"),
        }
        alignment = MultiTimeframeAlignmentEngine().analyze_alignment("XAUUSD", contexts)
        passed = (
            alignment.overall_direction == "CONFLICTED"
            and alignment.alignment_quality == "CONFLICTED"
            and bool(alignment.conflicts)
            and any("H4" in conflict for conflict in alignment.conflicts)
            and alignment.confidence < 60.0
        )
        print_result("HTF versus LTF reversal conflict lowers conviction and blocks direction", passed)
        return passed
    except Exception as exc:
        print_result("HTF versus LTF reversal conflict lowers conviction and blocks direction", False, str(exc))
        return False


def verify_narrative_and_neutral_handling() -> bool:
    try:
        from backend.institutional_intelligence.multi_timeframe_alignment_engine import (
            MultiTimeframeAlignmentEngine,
        )

        contexts = {timeframe: timeframe_context("NEUTRAL", 0.0) for timeframe in ("H4", "H1", "M15", "M5")}
        alignment = MultiTimeframeAlignmentEngine().analyze_alignment("XAUUSD", contexts)
        narrative = alignment.institutional_narrative
        passed = (
            alignment.overall_direction == "NEUTRAL"
            and alignment.alignment_quality == "MIXED"
            and narrative is not None
            and "No unified" in narrative.summary
            and "No directional" in alignment.warnings[0]
        )
        print_result("Neutral evidence produces a clear narrative and safe warning", passed)
        return passed
    except Exception as exc:
        print_result("Neutral evidence produces a clear narrative and safe warning", False, str(exc))
        return False


def verify_service_fallback() -> bool:
    try:
        from backend.institutional_intelligence.multi_timeframe_models import MultiTimeframeAlignment
        from backend.institutional_intelligence.smc_service import SMCService

        class UnavailableData:
            def get_candles(self, *args, **kwargs):
                raise RuntimeError("No market terminal required for alignment verification.")

            def close(self):
                return None

        alignment = SMCService(market_data_service=UnavailableData()).analyze_multi_timeframe_alignment("XAUUSD")
        passed = (
            isinstance(alignment, MultiTimeframeAlignment)
            and alignment.symbol == "XAUUSD"
            and alignment.overall_direction == "NEUTRAL"
            and alignment.alignment_score == 0.0
            and alignment.institutional_narrative is not None
        )
        print_result("SMCService degrades to neutral alignment without MT5", passed)
        return passed
    except Exception as exc:
        print_result("SMCService degrades to neutral alignment without MT5", False, str(exc))
        return False


def verify_api_json_and_health() -> bool:
    try:
        from backend.api import institutional_routes
        from backend.institutional_intelligence.smc_service import SMCService
        from backend.main import app

        class UnavailableData:
            def get_candles(self, *args, **kwargs):
                raise RuntimeError("API validation uses safe empty market contexts.")

            def close(self):
                return None

        client = TestClient(app)
        service = institutional_routes.smc_service
        institutional_routes.smc_service = SMCService(market_data_service=UnavailableData())
        try:
            endpoints = [
                "/institutional/alignment/XAUUSD",
                "/institutional/alignment/narrative/XAUUSD",
                "/institutional/alignment/conflicts/XAUUSD",
                "/institutional/alignment/timeframes/XAUUSD",
            ]
            responses = [client.get(endpoint) for endpoint in endpoints]
            readiness = client.get("/system/readiness")
        finally:
            institutional_routes.smc_service = service
        alignment = responses[0].json()
        conflict = responses[2].json()
        timeframes = responses[3].json()
        passed = (
            all(response.status_code == 200 for response in responses)
            and alignment["symbol"] == "XAUUSD"
            and "institutional_narrative" in alignment
            and conflict["simulation_only"] is True
            and conflict["live_execution_enabled"] is False
            and [item["timeframe"] for item in timeframes] == ["H4", "H1", "M15", "M5"]
            and any(module["module_name"] == "institutional_alignment" for module in readiness.json()["modules"])
        )
        print_result("Alignment APIs are JSON-safe, simulation-only, and monitored", passed)
        return passed
    except Exception as exc:
        print_result("Alignment APIs are JSON-safe, simulation-only, and monitored", False, str(exc))
        return False


def main() -> int:
    print("Phase 2 Day 8 Multi-Timeframe Institutional Alignment Verification")
    print("=" * 63)
    checks = [
        verify_path("backend/institutional_intelligence/multi_timeframe_models.py", "multi_timeframe_models.py exists"),
        verify_path("backend/institutional_intelligence/multi_timeframe_alignment_engine.py", "multi_timeframe_alignment_engine.py exists"),
        verify_path("backend/institutional_intelligence/timeframe_bias_resolver.py", "timeframe_bias_resolver.py exists"),
        verify_path("backend/institutional_intelligence/institutional_narrative_builder.py", "institutional_narrative_builder.py exists"),
        verify_path("backend/institutional_intelligence/timeframe_conflict_detector.py", "timeframe_conflict_detector.py exists"),
        verify_routes(),
        verify_hierarchy_and_full_alignment(),
        verify_conflict_detection_and_resolution(),
        verify_narrative_and_neutral_handling(),
        verify_service_fallback(),
        verify_api_json_and_health(),
    ]
    print("=" * 63)
    passed = all(checks)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
