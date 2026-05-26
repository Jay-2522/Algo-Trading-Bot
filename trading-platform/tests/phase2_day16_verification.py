import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def candles() -> list[dict]:
    start = datetime(2026, 5, 26, 7, 0, tzinfo=timezone.utc)
    points = [
        (100.0, 100.7, 99.8, 100.4),
        (100.4, 100.8, 99.5, 99.8),
        (99.8, 102.1, 99.7, 101.9),
        (101.9, 102.8, 101.5, 102.5),
        (102.5, 103.2, 102.1, 103.0),
        (103.0, 103.6, 102.6, 103.4),
        (103.4, 103.9, 103.0, 103.7),
    ]
    return [
        {"time": start + timedelta(minutes=15 * i), "open": o, "high": h, "low": l, "close": c}
        for i, (o, h, l, c) in enumerate(points)
    ]


class StaticData:
    def get_candles(self, *args, **kwargs):
        return candles()

    def close(self):
        return None


class UnavailableData:
    def get_candles(self, *args, **kwargs):
        raise RuntimeError("No MT5 required for reasoning verification.")

    def close(self):
        return None


def base_report(final_state: str, bias: str = "BULLISH"):
    from backend.institutional_intelligence.institutional_orchestration_models import (
        InstitutionalOrchestrationReport,
        InstitutionalSystemState,
    )

    return InstitutionalOrchestrationReport(
        symbol="XAUUSD",
        timeframe="M15",
        system_state=InstitutionalSystemState(
            symbol="XAUUSD",
            timeframe="M15",
            market_state="TRANSITIONING",
            institutional_bias=bias,
            setup_state="WAIT_FOR_CONFIRMATION",
            simulation_state="WAIT_FOR_CONFIRMATION",
            position_state="NO_POSITION",
            risk_state="SAFE",
            final_state=final_state,
            confidence=68.0,
        ),
    )


def verify_files_and_routes() -> bool:
    files = [
        "backend/institutional_intelligence/ai_reasoning_models.py",
        "backend/institutional_intelligence/market_narrative_engine.py",
        "backend/institutional_intelligence/institutional_reasoning_engine.py",
        "backend/institutional_intelligence/reasoning_summary_builder.py",
        "backend/institutional_intelligence/reasoning_explanation_builder.py",
        "backend/institutional_intelligence/reasoning_quality_checker.py",
        "docs/phase-2-day-16-progress.md",
    ]
    files_ok = all((PROJECT_ROOT / path).is_file() for path in files)
    try:
        from backend.main import app

        expected = {
            "/institutional/orchestration/{symbol}",
            "/institutional/reasoning/{symbol}",
            "/institutional/reasoning/narrative/{symbol}",
            "/institutional/reasoning/summary/{symbol}",
            "/institutional/reasoning/dashboard/{symbol}",
            "/institutional/reasoning/quality/{symbol}",
        }
        routes_ok = expected <= {route.path for route in app.routes}
    except Exception:
        routes_ok = False
    return show("Day 16 files and reasoning routes are registered with orchestration preserved", files_ok and routes_ok)


def verify_narrative_actions() -> bool:
    try:
        from backend.institutional_intelligence.market_narrative_engine import MarketNarrativeEngine

        engine = MarketNarrativeEngine()
        mapping = {
            "READY_FOR_SIMULATION": "READY_FOR_SIMULATION",
            "WAITING_FOR_CONFIRMATION": "WAIT",
            "BLOCKED": "AVOID",
            "NO_TRADE": "MONITOR",
            "MANAGING_POSITION": "MANAGE_POSITION",
            "ERROR_SAFE_MODE": "AVOID",
        }
        passed = all(
            engine.build_narrative(base_report(state)).recommended_action == action
            for state, action in mapping.items()
        )
        return show("Narrative actions consistently follow resolved institutional state", passed)
    except Exception as exc:
        return show("Narrative actions consistently follow resolved institutional state", False, str(exc))


def verify_reasoning_and_summaries() -> bool:
    try:
        from backend.institutional_intelligence.institutional_reasoning_engine import InstitutionalReasoningEngine
        from backend.institutional_intelligence.smc_service import SMCService

        orchestration = SMCService(market_data_service=StaticData()).analyze_institutional_orchestration_from_candles(
            "XAUUSD", "M15", candles()
        )
        reasoning = InstitutionalReasoningEngine().generate_reasoning(orchestration)
        passed = (
            reasoning.detailed_reasoning != ""
            and reasoning.executive_summary != ""
            and reasoning.client_friendly_summary != ""
            and reasoning.dashboard_summary != ""
            and reasoning.simulation_only is True
            and reasoning.live_execution_enabled is False
            and "simulation" in reasoning.client_friendly_summary.lower()
        )
        return show("Reasoning creates factual desk, client, and dashboard summaries", passed)
    except Exception as exc:
        return show("Reasoning creates factual desk, client, and dashboard summaries", False, str(exc))


def verify_quality_checker() -> bool:
    try:
        from backend.institutional_intelligence.institutional_reasoning_engine import InstitutionalReasoningEngine
        from backend.institutional_intelligence.reasoning_quality_checker import ReasoningQualityChecker

        engine = InstitutionalReasoningEngine()
        valid = engine.generate_reasoning(base_report("WAITING_FOR_CONFIRMATION"))
        quality = ReasoningQualityChecker().check_reasoning_quality(valid, "WAITING_FOR_CONFIRMATION")
        conflicting = valid.model_copy(
            update={"narrative": valid.narrative.model_copy(update={"recommended_action": "READY_FOR_SIMULATION"})}
        )
        conflict_quality = ReasoningQualityChecker().check_reasoning_quality(
            conflicting, "WAITING_FOR_CONFIRMATION"
        )
        unsafe = valid.model_copy(update={"client_friendly_summary": "Live trading " + "is active."})
        unsafe_quality = ReasoningQualityChecker().check_reasoning_quality(unsafe, "WAITING_FOR_CONFIRMATION")
        passed = (
            quality.passed
            and quality.clarity_score == 100.0
            and conflict_quality.contradiction_detected
            and unsafe_quality.contradiction_detected
        )
        return show("Quality checker catches contradictory action and prohibited live-trading claims", passed)
    except Exception as exc:
        return show("Quality checker catches contradictory action and prohibited live-trading claims", False, str(exc))


def verify_fallback_and_api_safety() -> bool:
    try:
        from backend.api import institutional_routes
        from backend.institutional_intelligence.smc_service import SMCService
        from backend.main import app

        fallback = SMCService(market_data_service=UnavailableData()).analyze_ai_reasoning("XAUUSD")
        client = TestClient(app)
        original = institutional_routes.smc_service
        institutional_routes.smc_service = SMCService(market_data_service=UnavailableData())
        try:
            endpoints = [
                "/institutional/reasoning/XAUUSD",
                "/institutional/reasoning/narrative/XAUUSD",
                "/institutional/reasoning/summary/XAUUSD",
                "/institutional/reasoning/dashboard/XAUUSD",
                "/institutional/reasoning/quality/XAUUSD",
            ]
            responses = [client.get(path) for path in endpoints]
            readiness = client.get("/system/readiness").json()
            safety = client.get("/system/safety-scan").json()
        finally:
            institutional_routes.smc_service = original
        output = responses[0].json()
        text = str(output).lower()
        passed = (
            fallback.simulation_only is True
            and fallback.live_execution_enabled is False
            and all(response.status_code == 200 for response in responses)
            and output["simulation_only"] is True
            and output["live_execution_enabled"] is False
            and ("live trading " + "is active") not in text
            and safety["passed"] is True
            and safety["order_send_found"] is False
            and any(module["module_name"] == "institutional_reasoning" for module in readiness["modules"])
        )
        return show("Reasoning APIs degrade safely, remain JSON-safe, and preserve analysis-only language", passed)
    except Exception as exc:
        return show("Reasoning APIs degrade safely, remain JSON-safe, and preserve analysis-only language", False, str(exc))


def main() -> int:
    print("Phase 2 Day 16 AI Institutional Reasoning Verification")
    print("=" * 55)
    tests = [
        verify_files_and_routes(),
        verify_narrative_actions(),
        verify_reasoning_and_summaries(),
        verify_quality_checker(),
        verify_fallback_and_api_safety(),
    ]
    print("=" * 55)
    print("PASS" if all(tests) else "FAIL")
    return 0 if all(tests) else 1


if __name__ == "__main__":
    raise SystemExit(main())
