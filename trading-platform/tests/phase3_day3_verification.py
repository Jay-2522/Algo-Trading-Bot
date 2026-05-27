import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def sample_blocked_steps():
    from backend.replay.replay_models import ReplayStepResult

    now = datetime.now(timezone.utc)
    return [
        ReplayStepResult(
            step_index=0,
            replay_time=now,
            candles_visible=40,
            simulation_decision={
                "action": "AVOID",
                "readiness": "BLOCKED",
                "rejection_reasons": ["Session killzone timing blocked setup."],
            },
            event_type="BLOCKED",
            confidence=20.0,
            notes=["Session block observed."],
        ),
        ReplayStepResult(
            step_index=1,
            replay_time=now,
            candles_visible=40,
            simulation_decision={
                "action": "NO_TRADE",
                "readiness": "NO_VALID_SETUP",
                "warnings": ["Confluence conflict detected."],
            },
            event_type="BLOCKED",
            confidence=25.0,
        ),
        ReplayStepResult(
            step_index=2,
            replay_time=now,
            candles_visible=40,
            simulation_decision={
                "action": "AVOID",
                "rejection_reasons": ["Risk RR geometry failed; undefined invalidation target."],
            },
            event_type="BLOCKED",
            confidence=10.0,
        ),
        ReplayStepResult(
            step_index=3,
            replay_time=now,
            candles_visible=40,
            simulation_decision={"action": "WAIT", "readiness": "WAIT_FOR_CONFIRMATION"},
            confidence=45.0,
        ),
    ]


def verify_files_and_routes() -> bool:
    files = [
        "backend/replay/replay_calibration_models.py",
        "backend/replay/replay_block_reason_analyzer.py",
        "backend/replay/replay_threshold_analyzer.py",
        "backend/replay/replay_calibration_engine.py",
        "backend/replay/replay_calibration_report_builder.py",
        "backend/replay/replay_threshold_recommendation_engine.py",
        "docs/phase-3-day-3-progress.md",
    ]
    files_ok = all((PROJECT_ROOT / path).is_file() for path in files)
    try:
        from backend.main import app

        routes = {route.path for route in app.routes}
        expected = {
            "/replay/calibration/latest",
            "/replay/calibration/{replay_id}",
            "/replay/calibration/block-reasons/{replay_id}",
            "/replay/calibration/suggestions/{replay_id}",
            "/replay/status",
        }
        routes_ok = expected <= routes
    except Exception:
        routes_ok = False
    return show("Calibration files and routes exist", files_ok and routes_ok)


def verify_calibration_components() -> bool:
    try:
        from backend.replay.replay_block_reason_analyzer import ReplayBlockReasonAnalyzer
        from backend.replay.replay_decision_analyzer import ReplayDecisionAnalyzer
        from backend.replay.replay_threshold_analyzer import ReplayThresholdAnalyzer
        from backend.replay.replay_threshold_recommendation_engine import ReplayThresholdRecommendationEngine

        analyzer = ReplayBlockReasonAnalyzer()
        empty = analyzer.analyze_block_reasons([])
        metrics = analyzer.analyze_block_reasons(sample_blocked_steps())
        decisions = ReplayDecisionAnalyzer().analyze_decisions(sample_blocked_steps())
        threshold = ReplayThresholdAnalyzer().analyze_threshold_strictness(metrics, decisions)
        suggestions = ReplayThresholdRecommendationEngine().generate_suggestions(metrics, threshold)
        passed = (
            empty.total_blocked == 0
            and empty.most_restrictive_gate == "NONE"
            and metrics.total_blocked == 3
            and metrics.block_rate == 75.0
            and metrics.gate_counts.get("SESSION", 0) >= 1
            and metrics.gate_counts.get("CONFLUENCE", 0) >= 1
            and threshold["status"] == "TOO_RESTRICTIVE"
            and threshold["flags"]["high_block_rate"] is True
            and suggestions
            and all(item.safety_note for item in suggestions)
            and all(item.adjustment_direction in {"RELAX", "TIGHTEN", "KEEP"} for item in suggestions)
            and any(item.threshold_name == "risk_gate" and item.adjustment_direction == "KEEP" for item in suggestions)
        )
        return show("Block, threshold, and recommendation engines are safe and deterministic", passed)
    except Exception as exc:
        return show("Block, threshold, and recommendation engines are safe and deterministic", False, str(exc))


def verify_report_and_service() -> bool:
    try:
        from backend.replay.replay_calibration_report_builder import ReplayCalibrationReportBuilder
        from backend.replay.replay_calibration_models import ReplayCalibrationReport
        from backend.replay.replay_models import ReplayRunResult
        from backend.replay.replay_report_builder import ReplayReportBuilder
        from backend.replay.replay_service import ReplayService

        run = ReplayRunResult(
            replay_id="RPL-CAL",
            symbol="XAUUSD",
            timeframe="M15",
            total_steps=4,
            step_results=sample_blocked_steps(),
        )
        replay_report = ReplayReportBuilder().build_report(run)
        calibration = ReplayCalibrationReportBuilder().build_report(run, replay_report)
        service = ReplayService()
        service.storage.save_result(run)
        service_calibration = service.get_replay_calibration("RPL-CAL")
        latest = service.get_latest_replay_calibration()
        missing = service.get_replay_calibration("MISSING")
        passed = (
            isinstance(calibration, ReplayCalibrationReport)
            and calibration.simulation_only is True
            and calibration.live_execution_enabled is False
            and calibration.calibration_status == "TOO_RESTRICTIVE"
            and service_calibration is not None
            and latest.replay_id == "RPL-CAL"
            and missing is None
        )
        return show("Calibration report builder and replay service are JSON-safe", passed)
    except Exception as exc:
        return show("Calibration report builder and replay service are JSON-safe", False, str(exc))


def verify_api_and_safety() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        latest_empty = client.get("/replay/calibration/latest")
        run = client.post(
            "/replay/run/XAUUSD",
            json={"window_size": 30, "step_size": 10, "max_steps": 2, "simulation_only": True},
        )
        replay_id = run.json()["replay_id"]
        calibration = client.get(f"/replay/calibration/{replay_id}")
        block_reasons = client.get(f"/replay/calibration/block-reasons/{replay_id}")
        suggestions = client.get(f"/replay/calibration/suggestions/{replay_id}")
        latest = client.get("/replay/calibration/latest")
        missing = client.get("/replay/calibration/MISSING")
        safety = client.get("/system/safety-scan").json()
        passed = (
            latest_empty.status_code == 200
            and run.status_code == 200
            and calibration.status_code == 200
            and block_reasons.status_code == 200
            and suggestions.status_code == 200
            and latest.status_code == 200
            and missing.status_code == 404
            and calibration.json()["simulation_only"] is True
            and calibration.json()["live_execution_enabled"] is False
            and isinstance(suggestions.json(), list)
            and safety["passed"] is True
            and safety["order_send_found"] is False
            and safety["live_execution_enabled"] is False
        )
        return show("Calibration API is JSON-safe and preserves simulation-only safety", passed)
    except Exception as exc:
        return show("Calibration API is JSON-safe and preserves simulation-only safety", False, str(exc))


def main() -> int:
    print("Phase 3 Day 3 Replay Calibration Verification")
    print("=" * 50)
    checks = [
        verify_files_and_routes(),
        verify_calibration_components(),
        verify_report_and_service(),
        verify_api_and_safety(),
    ]
    print("=" * 50)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
