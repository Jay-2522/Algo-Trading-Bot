import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def verify_files_and_routes() -> bool:
    files = [
        "backend/dashboard/__init__.py",
        "backend/dashboard/dashboard_models.py",
        "backend/dashboard/dashboard_status_builder.py",
        "backend/dashboard/dashboard_card_service.py",
        "backend/dashboard/dashboard_summary_service.py",
        "backend/dashboard/dashboard_service.py",
        "backend/api/dashboard_routes.py",
        "docs/phase-4-day-1-progress.md",
    ]
    files_ok = all((PROJECT_ROOT / path).is_file() for path in files)
    try:
        from backend.main import app

        routes = {route.path for route in app.routes}
        expected = {
            "/dashboard/status",
            "/dashboard/overview",
            "/dashboard/cards",
            "/dashboard/summary",
            "/phase3/status",
        }
        routes_ok = expected <= routes
    except Exception:
        routes_ok = False
    return show("Dashboard files and routes exist", files_ok and routes_ok)


def verify_dashboard_services() -> bool:
    try:
        from backend.dashboard.dashboard_card_service import DashboardCardService
        from backend.dashboard.dashboard_service import DashboardService
        from backend.dashboard.dashboard_status_builder import DashboardStatusBuilder
        from backend.dashboard.dashboard_summary_service import DashboardSummaryService

        status = DashboardStatusBuilder().build_status()
        overview = DashboardStatusBuilder().build_overview()
        cards = DashboardCardService().build_cards()
        summary = DashboardSummaryService().build_summary()
        service = DashboardService()
        json.dumps(
            {
                "status": status.model_dump(mode="json"),
                "overview": overview.model_dump(mode="json"),
                "cards": [card.model_dump(mode="json") for card in cards],
                "summary": summary,
                "service_status": service.get_status().model_dump(mode="json"),
            },
            default=str,
        )
        card_ids = {card.card_id for card in cards}
        expected_cards = {
            "system_health",
            "broker_compatibility",
            "webhook_intake",
            "account_routing",
            "allocation",
            "execution_queue",
            "monitoring_alerts",
            "phase3_readiness",
        }
        passed = (
            status.dashboard_ready is True
            and status.simulation_only is True
            and status.live_execution_enabled is False
            and overview.simulation_only is True
            and overview.live_execution_enabled is False
            and len(overview.cards) >= 8
            and expected_cards <= card_ids
            and "simulation-only" in summary["safety_status"].lower()
            and summary["live_execution_enabled"] is False
        )
        return show("Dashboard services produce JSON-safe overview, cards, and summary", passed)
    except Exception as exc:
        return show("Dashboard services produce JSON-safe overview, cards, and summary", False, str(exc))


def verify_dashboard_api_and_safety() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        endpoints = ["/dashboard/status", "/dashboard/overview", "/dashboard/cards", "/dashboard/summary", "/phase3/status"]
        responses = [client.get(endpoint) for endpoint in endpoints]
        payloads = [response.json() for response in responses]
        safety_text = "\n".join(
            path.read_text(encoding="utf-8", errors="ignore")
            for path in (PROJECT_ROOT / "backend").rglob("*.py")
        )
        json.dumps(payloads, default=str)
        passed = (
            all(response.status_code == 200 for response in responses)
            and payloads[0]["dashboard_ready"] is True
            and payloads[0]["simulation_only"] is True
            and payloads[0]["live_execution_enabled"] is False
            and payloads[1]["simulation_only"] is True
            and payloads[1]["live_execution_enabled"] is False
            and isinstance(payloads[2], list)
            and len(payloads[2]) >= 8
            and payloads[4]["simulation_only"] is True
            and "mt5.order_send" not in safety_text
            and "order_send(" not in safety_text
            and "live_execution_enabled=True" not in safety_text
        )
        return show("Dashboard APIs are JSON-safe and safety flags are preserved", passed)
    except Exception as exc:
        return show("Dashboard APIs are JSON-safe and safety flags are preserved", False, str(exc))


def main() -> int:
    print("Phase 4 Day 1 VPS Dashboard Backend Verification")
    print("=" * 55)
    checks = [
        verify_files_and_routes(),
        verify_dashboard_services(),
        verify_dashboard_api_and_safety(),
    ]
    print("=" * 55)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
