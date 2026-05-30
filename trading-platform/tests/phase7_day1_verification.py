import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def verify_files() -> bool:
    files = [
        "backend/news_intelligence/__init__.py",
        "backend/news_intelligence/models.py",
        "backend/news_intelligence/news_service.py",
        "backend/news_intelligence/event_classifier.py",
        "backend/news_intelligence/news_risk_engine.py",
        "backend/news_intelligence/news_readiness_service.py",
        "docs/phase-7-day-1-progress.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    return show("News intelligence module and docs files exist", not missing, ", ".join(missing))


def verify_models_and_services() -> bool:
    try:
        from backend.news_intelligence.event_classifier import EventClassifier
        from backend.news_intelligence.models import NewsEvent, NewsIntelligenceStatus
        from backend.news_intelligence.news_readiness_service import NewsReadinessService
        from backend.news_intelligence.news_risk_engine import NewsRiskEngine
        from backend.news_intelligence.news_service import NewsService

        event_fields = {
            "event_id",
            "title",
            "category",
            "currency",
            "impact",
            "scheduled_time",
            "source",
            "risk_level",
            "active",
            "warnings",
        }
        status_fields = {
            "status",
            "architecture_ready",
            "sources_supported",
            "event_types_supported",
            "risk_engine_ready",
            "strategy_integration_ready",
            "simulation_only",
            "live_execution_enabled",
            "timestamp",
        }
        passed = (
            event_fields <= set(NewsEvent.model_fields)
            and status_fields <= set(NewsIntelligenceStatus.model_fields)
            and EventClassifier().classify("US CPI") == ("CPI", "HIGH")
            and NewsRiskEngine() is not None
            and NewsService().get_status().architecture_ready is True
            and NewsReadinessService().status()["architecture_ready"] is True
        )
        return show("News models, classifier, risk engine, service, and readiness service work", passed)
    except Exception as exc:
        return show("News models, classifier, risk engine, service, and readiness service work", False, str(exc))


def verify_supported_lists_and_risk() -> bool:
    try:
        from backend.news_intelligence.news_service import NewsService

        service = NewsService()
        sources = service.get_supported_sources()
        events = service.get_supported_events()
        calendar = service.build_placeholder_calendar()
        categories = {event.category for event in calendar}
        risks = {event.category: event.risk_level for event in calendar}
        passed = (
            "FOREX_FACTORY_PENDING" in sources
            and "FINANCIAL_JUICE_PENDING" in sources
            and "CPI" in events
            and "NFP" in events
            and "FOMC" in events
            and {"CPI", "NFP", "FOMC", "PMI"} <= categories
            and risks["NFP"] == "EXTREME"
            and risks["FOMC"] == "EXTREME"
            and risks["CPI"] == "HIGH"
        )
        return show("Supported sources, events, placeholder calendar, and risk rules are populated", passed)
    except Exception as exc:
        return show("Supported sources, events, placeholder calendar, and risk rules are populated", False, str(exc))


def verify_routes() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        status = client.get("/news/status")
        sources = client.get("/news/supported-sources")
        events = client.get("/news/supported-events")
        calendar = client.get("/news/calendar-placeholder")
        readiness = client.get("/news/readiness")
        passed = (
            status.status_code == 200
            and sources.status_code == 200
            and events.status_code == 200
            and calendar.status_code == 200
            and readiness.status_code == 200
            and status.json()["simulation_only"] is True
            and status.json()["live_execution_enabled"] is False
            and sources.json()["external_feeds_enabled"] is False
            and len(events.json()["event_types"]) >= 10
            and len(sources.json()["sources"]) >= 4
            and readiness.json()["external_api_calls_enabled"] is False
        )
        return show("News intelligence API routes work", passed)
    except Exception as exc:
        return show("News intelligence API routes work", False, str(exc))


def verify_strategy_placeholder() -> bool:
    try:
        from backend.strategy_engine.xauusd_strategy_engine import XAUUSDStrategyEngine

        signal = XAUUSDStrategyEngine().analyze()
        news_context = signal.metadata.get("news_context", {})
        passed = (
            news_context.get("status") == "PENDING_INTEGRATION"
            and news_context.get("high_impact_event_active") is False
            and news_context.get("news_risk_mode") == "UNKNOWN"
            and signal.metadata["simulation_only"] is True
            and signal.metadata["live_execution_enabled"] is False
            and signal.metadata["broker_execution_enabled"] is False
            and signal.execution_allowed is False
        )
        return show("Strategy news placeholder integration exists and remains non-executing", passed)
    except Exception as exc:
        return show("Strategy news placeholder integration exists and remains non-executing", False, str(exc))


def verify_order_send_isolated() -> bool:
    token = "mt5." + "order_send"
    matches = []
    for path in (PROJECT_ROOT / "backend").rglob("*.py"):
        if path.is_file() and token in path.read_text(encoding="utf-8", errors="ignore"):
            matches.append(path.relative_to(PROJECT_ROOT).as_posix())
    passed = matches == ["backend/demo_execution/mt5_demo_executor.py"]
    return show("MT5 order submission remains isolated to guarded demo executor", passed, ", ".join(matches))


def verify_phase6_routes_preserved() -> bool:
    try:
        from backend.main import app
        from tests.regression_routes_verification import REQUIRED_GET_ROUTES, REQUIRED_WEBSOCKET_ROUTES

        registered_get_routes = {
            route.path
            for route in app.routes
            if hasattr(route, "methods") and "GET" in route.methods
        }
        registered_websockets = {
            route.path
            for route in app.routes
            if route.__class__.__name__ == "APIWebSocketRoute"
        }
        all_route_paths = {route.path for route in app.routes}
        expected_phase6 = {
            "/strategy/analyze/xauusd",
            "/strategy/liquidity/xauusd",
            "/strategy/structure/xauusd",
            "/strategy/fvg/xauusd",
            "/strategy/order-block/xauusd",
            "/strategy/regime/xauusd",
            "/strategy/confluence/xauusd",
        }
        missing = sorted(REQUIRED_GET_ROUTES - registered_get_routes)
        missing += sorted(expected_phase6 - all_route_paths)
        missing_ws = sorted(REQUIRED_WEBSOCKET_ROUTES - registered_websockets)
        return show("Phase 6 and regression routes are preserved", not missing and not missing_ws, ", ".join(missing + missing_ws))
    except Exception as exc:
        return show("Phase 6 and regression routes are preserved", False, str(exc))


def main() -> int:
    print("Phase 7 Day 1 News Intelligence Foundation Verification")
    print("=" * 62)
    checks = [
        verify_files(),
        verify_models_and_services(),
        verify_supported_lists_and_risk(),
        verify_routes(),
        verify_strategy_placeholder(),
        verify_order_send_isolated(),
        verify_phase6_routes_preserved(),
    ]
    print("=" * 62)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
