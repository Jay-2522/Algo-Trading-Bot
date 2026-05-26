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
    base = datetime(2026, 5, 26, 7, 0, tzinfo=timezone.utc)
    values = [
        (100.0, 100.8, 99.8, 100.5),
        (100.5, 101.0, 100.1, 100.7),
        (100.7, 100.9, 99.5, 99.8),
        (99.8, 102.4, 99.7, 102.0),
        (102.0, 102.8, 101.6, 102.5),
        (102.5, 103.1, 102.0, 102.9),
        (102.9, 103.5, 102.4, 103.2),
        (103.2, 103.8, 102.8, 103.6),
        (103.6, 104.0, 103.1, 103.8),
    ]
    return [
        {"time": base + timedelta(minutes=15 * i), "open": o, "high": h, "low": l, "close": c}
        for i, (o, h, l, c) in enumerate(values)
    ]


class StaticData:
    def get_candles(self, *args, **kwargs):
        return candles()

    def close(self):
        return None


class UnavailableData:
    def get_candles(self, *args, **kwargs):
        raise RuntimeError("No MT5 required for institutional orchestration verification.")

    def close(self):
        return None


def verify_files_and_routes() -> bool:
    required_files = [
        "backend/institutional_intelligence/institutional_orchestration_models.py",
        "backend/institutional_intelligence/institutional_orchestrator.py",
        "backend/institutional_intelligence/institutional_pipeline_runner.py",
        "backend/institutional_intelligence/institutional_state_resolver.py",
        "backend/institutional_intelligence/institutional_report_builder.py",
        "backend/institutional_intelligence/institutional_health_checker.py",
        "docs/phase-2-day-15-progress.md",
    ]
    files_ok = all((PROJECT_ROOT / path).is_file() for path in required_files)
    try:
        from backend.main import app

        expected = {
            "/institutional/position-management/{symbol}",
            "/institutional/orchestration/{symbol}",
            "/institutional/orchestration/state/{symbol}",
            "/institutional/orchestration/report/{symbol}",
            "/institutional/orchestration/summary/{symbol}",
            "/institutional/orchestration/health/{symbol}",
        }
        routes_ok = expected <= {route.path for route in app.routes}
    except Exception:
        routes_ok = False
    return show("Day 15 files and institutional orchestration routes exist", files_ok and routes_ok)


def verify_complete_pipeline() -> bool:
    try:
        from backend.institutional_intelligence.smc_service import SMCService

        report = SMCService(market_data_service=StaticData()).analyze_institutional_orchestration_from_candles(
            "XAUUSD", "M15", candles()
        )
        expected = [
            "institutional_context",
            "sweep_context",
            "fvg_context",
            "order_block_context",
            "breaker_context",
            "structure_shift_context",
            "confluence_context",
            "alignment_context",
            "session_context",
            "entry_model_context",
            "setup_validation_context",
            "simulation_decision_context",
            "paper_trade_context",
            "position_management_context",
        ]
        passed = (
            [step.step_name for step in report.pipeline_steps] == expected
            and all(step.duration_ms >= 0 for step in report.pipeline_steps)
            and report.system_state is not None
            and report.executive_summary != ""
            and report.simulation_only is True
            and report.live_execution_enabled is False
        )
        return show("Pipeline executes all fourteen institutional stages in order", passed)
    except Exception as exc:
        return show("Pipeline executes all fourteen institutional stages in order", False, str(exc))


def verify_failure_isolation_and_health() -> bool:
    try:
        from backend.institutional_intelligence.smc_service import SMCService

        service = SMCService(market_data_service=StaticData())

        def broken_fvg(*args, **kwargs):
            raise RuntimeError("Synthetic FVG failure.")

        service.analyze_fvgs_from_candles = broken_fvg
        report = service.analyze_institutional_orchestration_from_candles("XAUUSD", "M15", candles())
        health = service.institutional_orchestrator.health_checker.check_institutional_health(report)
        fvg_step = next(step for step in report.pipeline_steps if step.step_name == "fvg_context")
        passed = (
            fvg_step.status == "FAILED"
            and len(report.pipeline_steps) == 14
            and report.system_state.final_state == "ERROR_SAFE_MODE"
            and not health.passed
            and "fvg_context" in health.failed_steps
        )
        return show("Failed module is isolated and resolves to safe-mode health", passed)
    except Exception as exc:
        return show("Failed module is isolated and resolves to safe-mode health", False, str(exc))


def verify_state_resolution() -> bool:
    try:
        from backend.institutional_intelligence.institutional_orchestration_models import InstitutionalOrchestrationReport
        from backend.institutional_intelligence.institutional_state_resolver import InstitutionalStateResolver
        from backend.institutional_intelligence.position_management_models import InstitutionalPositionManagement, ManagedPosition

        active = ManagedPosition(
            position_id="PPP-ACTIVE",
            candidate_id="PPC-ACTIVE",
            symbol="XAUUSD",
            timeframe="M15",
            direction="BUY",
            entry_price=100.0,
            initial_stop=99.0,
            current_stop=100.0,
            target_level=104.0,
            initial_risk=1.0,
            opened_at=datetime.now(timezone.utc),
        )
        managing_report = InstitutionalOrchestrationReport(
            symbol="XAUUSD",
            timeframe="M15",
            position_management_context=InstitutionalPositionManagement(
                symbol="XAUUSD",
                timeframe="M15",
                managed_positions=[active],
                active_positions=[active],
                management_status="MANAGING",
            ),
        )
        managing = InstitutionalStateResolver().resolve_state(managing_report)
        passed = managing.final_state == "MANAGING_POSITION"
        return show("State resolver prioritizes active paper-position management", passed)
    except Exception as exc:
        return show("State resolver prioritizes active paper-position management", False, str(exc))


def verify_fallback_and_api() -> bool:
    try:
        from backend.api import institutional_routes
        from backend.institutional_intelligence.smc_service import SMCService
        from backend.main import app

        service = SMCService(market_data_service=UnavailableData())
        fallback = service.analyze_institutional_orchestration("XAUUSD")
        client = TestClient(app)
        original = institutional_routes.smc_service
        institutional_routes.smc_service = SMCService(market_data_service=UnavailableData())
        try:
            endpoints = [
                "/institutional/orchestration/XAUUSD",
                "/institutional/orchestration/state/XAUUSD",
                "/institutional/orchestration/report/XAUUSD",
                "/institutional/orchestration/summary/XAUUSD",
                "/institutional/orchestration/health/XAUUSD",
            ]
            responses = [client.get(path) for path in endpoints]
            readiness = client.get("/system/readiness").json()
            safety = client.get("/system/safety-scan").json()
        finally:
            institutional_routes.smc_service = original
        report = responses[0].json()
        summary = responses[3].json()
        passed = (
            fallback.simulation_only is True
            and fallback.live_execution_enabled is False
            and all(response.status_code == 200 for response in responses)
            and report["simulation_only"] is True
            and summary["live_execution_enabled"] is False
            and safety["passed"] is True
            and safety["order_send_found"] is False
            and any(module["module_name"] == "institutional_orchestration" for module in readiness["modules"])
        )
        return show("Routes are JSON-safe and MT5-unavailable fallback remains simulation-only", passed)
    except Exception as exc:
        return show("Routes are JSON-safe and MT5-unavailable fallback remains simulation-only", False, str(exc))


def main() -> int:
    print("Phase 2 Day 15 Institutional Orchestration Verification")
    print("=" * 56)
    tests = [
        verify_files_and_routes(),
        verify_complete_pipeline(),
        verify_failure_isolation_and_health(),
        verify_state_resolution(),
        verify_fallback_and_api(),
    ]
    print("=" * 56)
    print("PASS" if all(tests) else "FAIL")
    return 0 if all(tests) else 1


if __name__ == "__main__":
    raise SystemExit(main())
