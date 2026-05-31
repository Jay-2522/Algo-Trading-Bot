import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def verify_files_and_model() -> bool:
    files = [
        "backend/news_intelligence/news_command_center.py",
        "backend/news_intelligence/news_health_monitor.py",
        "backend/news_intelligence/news_readiness_dashboard.py",
        "docs/phase-7-day-7-progress.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    try:
        from backend.news_intelligence.news_readiness_dashboard import Phase7NewsStatus

        model_ok = (
            "phase" in Phase7NewsStatus.model_fields
            and "status" in Phase7NewsStatus.model_fields
            and "health_score" in Phase7NewsStatus.model_fields
            and "readiness_score" in Phase7NewsStatus.model_fields
        )
    except Exception:
        model_ok = False
    return show("Command center, health, readiness files and Phase7NewsStatus model exist", not missing and model_ok, ", ".join(missing))


def verify_command_center_health_readiness() -> bool:
    try:
        from backend.news_intelligence.news_service import NewsService

        service = NewsService()
        overview = service.get_command_center_overview()
        health = service.get_news_health()
        readiness = service.get_readiness_dashboard()
        phase = service.get_phase7_status()
        passed = (
            overview["status"] == "OPERATIONAL"
            and overview["calendar_status"]["engine_ready"] is True
            and overview["headline_status"]["engine_ready"] is True
            and overview["macro_status"]["engine_ready"] is True
            and overview["unified_risk_status"]["engine_ready"] is True
            and overview["strategy_news_status"]["strategy_integration_ready"] is True
            and health["status"] == "READY"
            and health["health_score"] == 100
            and readiness["overall"] == "PHASE_7_READY"
            and readiness["readiness_score"] == 100
            and phase.phase == "Phase 7"
            and phase.status == "COMPLETE"
            and phase.health_score == 100
            and phase.readiness_score == 100
            and phase.simulation_only is True
            and phase.live_execution_enabled is False
        )
        return show("Command center, health monitor, readiness dashboard, and phase status work", passed)
    except Exception as exc:
        return show("Command center, health monitor, readiness dashboard, and phase status work", False, str(exc))


def verify_routes_and_strategy_metadata() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        command_center = client.get("/news/command-center")
        health = client.get("/news/health")
        readiness = client.get("/news/readiness-dashboard")
        phase = client.get("/news/phase7/status")
        signal = client.post("/strategy/analyze/xauusd", json={})
        payload = signal.json()
        phase_meta = payload["metadata"].get("news_phase_status", {})
        passed = (
            command_center.status_code == 200
            and command_center.json()["status"] == "OPERATIONAL"
            and health.status_code == 200
            and health.json()["health_score"] == 100
            and readiness.status_code == 200
            and readiness.json()["overall"] == "PHASE_7_READY"
            and phase.status_code == 200
            and phase.json()["phase"] == "Phase 7"
            and phase.json()["status"] == "COMPLETE"
            and phase.json()["simulation_only"] is True
            and phase.json()["live_execution_enabled"] is False
            and signal.status_code == 200
            and phase_meta["calendar_ready"] is True
            and phase_meta["headline_ready"] is True
            and phase_meta["macro_ready"] is True
            and phase_meta["unified_ready"] is True
            and phase_meta["simulation_only"] is True
            and phase_meta["live_execution_enabled"] is False
            and payload["execution_allowed"] is False
        )
        return show("Command center routes and strategy phase metadata work", passed)
    except Exception as exc:
        return show("Command center routes and strategy phase metadata work", False, str(exc))


def verify_no_external_api_calls() -> bool:
    forbidden = ["requests.", "httpx.", "aiohttp", "urllib.request", "BeautifulSoup", "selenium"]
    offenders = []
    for path in (PROJECT_ROOT / "backend/news_intelligence").rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in forbidden:
            if token in text:
                offenders.append(f"{path.relative_to(PROJECT_ROOT).as_posix()}:{token}")
    return show("News intelligence command center contains no external API or scraping calls", not offenders, ", ".join(offenders))


def verify_order_send_isolated() -> bool:
    token = "mt5." + "order_send"
    matches = []
    for path in (PROJECT_ROOT / "backend").rglob("*.py"):
        if path.is_file() and token in path.read_text(encoding="utf-8", errors="ignore"):
            matches.append(path.relative_to(PROJECT_ROOT).as_posix())
    passed = matches == ["backend/demo_execution/mt5_demo_executor.py"]
    return show("MT5 order submission remains isolated to guarded demo executor", passed, ", ".join(matches))


def verify_preserved_routes() -> bool:
    try:
        from backend.main import app
        from tests.regression_routes_verification import REQUIRED_GET_ROUTES, REQUIRED_WEBSOCKET_ROUTES

        registered_get_routes = {
            route.path
            for route in app.routes
            if hasattr(route, "methods") and "GET" in route.methods
        }
        all_route_paths = {route.path for route in app.routes}
        registered_websockets = {
            route.path
            for route in app.routes
            if route.__class__.__name__ == "APIWebSocketRoute"
        }
        expected = {
            "/news/status",
            "/news/command-center",
            "/news/health",
            "/news/readiness-dashboard",
            "/news/phase7/status",
            "/news/unified-risk/xauusd",
            "/news/headlines/risk-context",
            "/strategy/confluence/xauusd",
            "/strategy/regime/xauusd",
        }
        missing = sorted(REQUIRED_GET_ROUTES - registered_get_routes)
        missing += sorted(expected - all_route_paths)
        missing_ws = sorted(REQUIRED_WEBSOCKET_ROUTES - registered_websockets)
        return show("Phase 7 Day 1-6 and Phase 6 routes are preserved", not missing and not missing_ws, ", ".join(missing + missing_ws))
    except Exception as exc:
        return show("Phase 7 Day 1-6 and Phase 6 routes are preserved", False, str(exc))


def main() -> int:
    print("Phase 7 Day 7 News Command Center Verification")
    print("=" * 58)
    checks = [
        verify_files_and_model(),
        verify_command_center_health_readiness(),
        verify_routes_and_strategy_metadata(),
        verify_no_external_api_calls(),
        verify_order_send_isolated(),
        verify_preserved_routes(),
    ]
    print("=" * 58)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
