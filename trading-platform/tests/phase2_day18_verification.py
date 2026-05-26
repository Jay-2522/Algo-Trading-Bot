import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


class UnavailableData:
    def get_candles(self, *args, **kwargs):
        raise RuntimeError("No MT5 required for dashboard verification.")

    def close(self):
        return None


def make_report(final_state: str, live_execution_enabled: bool = False):
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
            final_state=final_state,
            market_state="TRANSITIONING",
            institutional_bias="BULLISH",
            confidence=72.0,
        ),
        executive_summary=f"Institutional state is {final_state}.",
        live_execution_enabled=live_execution_enabled,
    )


def verify_files_routes() -> bool:
    files = [
        "backend/institutional_intelligence/dashboard_context_models.py",
        "backend/institutional_intelligence/dashboard_card_builder.py",
        "backend/institutional_intelligence/dashboard_context_builder.py",
        "backend/institutional_intelligence/dashboard_status_resolver.py",
        "backend/institutional_intelligence/dashboard_alert_builder.py",
        "backend/institutional_intelligence/dashboard_summary_builder.py",
        "docs/phase-2-day-18-progress.md",
    ]
    files_ok = all((PROJECT_ROOT / path).is_file() for path in files)
    try:
        from backend.main import app

        routes = {route.path for route in app.routes}
        expected = {
            "/institutional/performance/{symbol}",
            "/institutional/dashboard/{symbol}",
            "/institutional/dashboard/cards/{symbol}",
            "/institutional/dashboard/alerts/{symbol}",
            "/institutional/dashboard/recommendation/{symbol}",
            "/institutional/dashboard/status/{symbol}",
        }
        routes_ok = expected <= routes
    except Exception:
        routes_ok = False
    return show("Day 18 files and dashboard routes exist with prior analytics preserved", files_ok and routes_ok)


def verify_recommendation_and_status_logic() -> bool:
    try:
        from backend.institutional_intelligence.dashboard_status_resolver import DashboardStatusResolver
        from backend.institutional_intelligence.dashboard_summary_builder import DashboardSummaryBuilder

        summary = DashboardSummaryBuilder()
        resolver = DashboardStatusResolver()
        ready = make_report("READY_FOR_SIMULATION")
        waiting = make_report("WAITING_FOR_CONFIRMATION")
        blocked = make_report("BLOCKED")
        managing = make_report("MANAGING_POSITION")
        unsafe = make_report("READY_FOR_SIMULATION", live_execution_enabled=True)
        passed = (
            summary.build_final_recommendation(ready).action == "READY_FOR_SIMULATION"
            and summary.build_final_recommendation(ready).simulation_allowed is True
            and summary.build_final_recommendation(waiting).action == "WAIT"
            and summary.build_final_recommendation(blocked).action == "AVOID"
            and summary.build_final_recommendation(managing).action == "MANAGE_POSITION"
            and summary.build_final_recommendation(unsafe).action == "REVIEW_SYSTEM"
            and resolver.resolve_dashboard_status([], blocked) == "BLOCKED"
            and resolver.resolve_dashboard_status([], waiting) == "WAITING"
            and resolver.resolve_dashboard_status([], managing) == "ACTIVE"
            and resolver.resolve_dashboard_status([], unsafe) == "CRITICAL"
        )
        return show("Recommendation and status resolution respect institutional and safety state", passed)
    except Exception as exc:
        return show("Recommendation and status resolution respect institutional and safety state", False, str(exc))


def verify_context_cards_alerts_and_serialization() -> bool:
    try:
        from backend.institutional_intelligence.dashboard_alert_builder import DashboardAlertBuilder
        from backend.institutional_intelligence.dashboard_context_builder import DashboardContextBuilder
        from backend.institutional_intelligence.performance_analytics_context_builder import PerformanceAnalyticsContextBuilder
        from backend.institutional_intelligence.smc_service import SMCService

        service = SMCService(market_data_service=UnavailableData())
        context = service.analyze_dashboard_context_from_candles("XAUUSD", "M15", [])
        standalone = DashboardContextBuilder().build_dashboard_context("XAUUSD", "M15", [])
        performance = PerformanceAnalyticsContextBuilder().build_performance_context("XAUUSD", "M15")
        alerts = DashboardAlertBuilder().build_alerts(make_report("BLOCKED"), performance)
        serialized = json.dumps(context.model_dump(mode="json"))
        categories = {alert.category for alert in alerts}
        passed = (
            len(context.cards) == 14
            and len(standalone.cards) == 14
            and standalone.final_recommendation.action == "REVIEW_SYSTEM"
            and context.simulation_only is True
            and context.live_execution_enabled is False
            and context.final_recommendation.action
            in {"MONITOR", "WAIT", "AVOID", "READY_FOR_SIMULATION", "MANAGE_POSITION", "REVIEW_SYSTEM"}
            and "SAFETY" in categories
            and "READINESS" in categories
            and "DATA_QUALITY" in categories
            and '"simulation_only": true' in serialized
        )
        return show("Context builds dashboard cards, alerts, and JSON-safe recommendation output", passed)
    except Exception as exc:
        return show("Context builds dashboard cards, alerts, and JSON-safe recommendation output", False, str(exc))


def verify_api_fallback_and_safety() -> bool:
    try:
        from backend.api import institutional_routes
        from backend.institutional_intelligence.smc_service import SMCService
        from backend.main import app

        client = TestClient(app)
        original = institutional_routes.smc_service
        institutional_routes.smc_service = SMCService(market_data_service=UnavailableData())
        try:
            endpoints = [
                "/institutional/dashboard/XAUUSD",
                "/institutional/dashboard/cards/XAUUSD",
                "/institutional/dashboard/alerts/XAUUSD",
                "/institutional/dashboard/recommendation/XAUUSD",
                "/institutional/dashboard/status/XAUUSD",
            ]
            responses = [client.get(path) for path in endpoints]
            readiness = client.get("/system/readiness").json()
            safety = client.get("/system/safety-scan").json()
        finally:
            institutional_routes.smc_service = original
        data = responses[0].json()
        recommendation = responses[3].json()
        serialized = str(data).lower()
        passed = (
            all(response.status_code == 200 for response in responses)
            and data["simulation_only"] is True
            and data["live_execution_enabled"] is False
            and recommendation["action"] != "READY_FOR_LIVE_EXECUTION"
            and ("live trading " + "is active") not in serialized
            and safety["passed"] is True
            and safety["order_send_found"] is False
            and safety["live_execution_enabled"] is False
            and any(module["module_name"] == "institutional_dashboard" for module in readiness["modules"])
        )
        return show("Dashboard API degrades safely and preserves simulation-only safeguards", passed)
    except Exception as exc:
        return show("Dashboard API degrades safely and preserves simulation-only safeguards", False, str(exc))


def main() -> int:
    print("Phase 2 Day 18 Unified Institutional Dashboard Context Verification")
    print("=" * 66)
    tests = [
        verify_files_routes(),
        verify_recommendation_and_status_logic(),
        verify_context_cards_alerts_and_serialization(),
        verify_api_fallback_and_safety(),
    ]
    print("=" * 66)
    print("PASS" if all(tests) else "FAIL")
    return 0 if all(tests) else 1


if __name__ == "__main__":
    raise SystemExit(main())
