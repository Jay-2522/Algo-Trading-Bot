import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def iso_minutes(minutes: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z")


def cpi_fixture(minutes: int = 20) -> dict:
    return {
        "title": "Core CPI m/m",
        "currency": "USD",
        "impact": "High",
        "time": iso_minutes(minutes),
        "actual": "",
        "forecast": "0.3%",
        "previous": "0.2%",
    }


def nfp_fixture(minutes: int = 45) -> dict:
    return {
        "title": "Non-Farm Employment Change",
        "currency": "USD",
        "impact": "High",
        "time": iso_minutes(minutes),
        "actual": "",
        "forecast": "180K",
        "previous": "175K",
    }


def pmi_fixture(minutes: int = 10) -> dict:
    return {
        "title": "EUR Flash Manufacturing PMI",
        "currency": "EUR",
        "impact": "Medium",
        "time": iso_minutes(minutes),
        "forecast": "51.0",
        "previous": "50.6",
    }


def low_fixture(minutes: int = 120) -> dict:
    return {
        "title": "Final Wholesale Inventories",
        "currency": "USD",
        "impact": "Low",
        "time": iso_minutes(minutes),
        "forecast": "0.1%",
        "previous": "0.1%",
    }


def missing_time_fixture() -> dict:
    return {
        "title": "Minor USD Speaker",
        "currency": "USD",
        "impact": "Low",
        "actual": "",
        "forecast": "",
        "previous": "",
    }


def verify_files() -> bool:
    files = [
        "backend/news_intelligence/forex_factory_adapter.py",
        "backend/news_intelligence/economic_calendar_store.py",
        "backend/news_intelligence/news_window_engine.py",
        "docs/phase-7-day-2-progress.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    return show("Forex Factory adapter, calendar store, window engine, and docs exist", not missing, ", ".join(missing))


def verify_models() -> bool:
    try:
        from backend.news_intelligence.models import EconomicCalendarEvent, NewsRiskContext

        event_fields = {
            "event_id",
            "source",
            "title",
            "currency",
            "impact",
            "category",
            "scheduled_time",
            "actual",
            "forecast",
            "previous",
            "risk_level",
            "pre_event_window_minutes",
            "post_event_window_minutes",
            "active_risk_window",
            "trade_action",
            "warnings",
        }
        context_fields = {
            "high_impact_event_active",
            "active_events",
            "upcoming_events",
            "risk_level",
            "trade_action",
            "reason",
            "sources_checked",
            "simulation_only",
            "live_execution_enabled",
            "timestamp",
        }
        return show("EconomicCalendarEvent and NewsRiskContext models exist", event_fields <= set(EconomicCalendarEvent.model_fields) and context_fields <= set(NewsRiskContext.model_fields))
    except Exception as exc:
        return show("EconomicCalendarEvent and NewsRiskContext models exist", False, str(exc))


def verify_adapter_and_risk_windows() -> bool:
    try:
        from backend.news_intelligence.forex_factory_adapter import ForexFactoryAdapter
        from backend.news_intelligence.news_window_engine import NewsWindowEngine

        adapter = ForexFactoryAdapter()
        window_engine = NewsWindowEngine()
        cpi = window_engine.apply_windows(adapter.normalize_event(cpi_fixture()))
        nfp = window_engine.apply_windows(adapter.normalize_event(nfp_fixture()))
        pmi = window_engine.apply_windows(adapter.normalize_event(pmi_fixture()))
        low = window_engine.apply_windows(adapter.normalize_event(low_fixture()))
        missing = window_engine.apply_windows(adapter.normalize_event(missing_time_fixture()))
        passed = (
            cpi.source == "FOREX_FACTORY"
            and cpi.currency == "USD"
            and cpi.category == "CPI"
            and cpi.risk_level == "HIGH"
            and cpi.trade_action == "BLOCK"
            and cpi.active_risk_window is True
            and nfp.category == "NFP"
            and nfp.risk_level == "EXTREME"
            and nfp.trade_action == "BLOCK"
            and pmi.risk_level == "MEDIUM"
            and pmi.trade_action == "REDUCE_RISK"
            and low.risk_level == "LOW"
            and low.trade_action == "ALLOW"
            and missing.scheduled_time is None
            and missing.warnings
        )
        return show("Forex Factory normalization, risk scoring, and windows work", passed)
    except Exception as exc:
        return show("Forex Factory normalization, risk scoring, and windows work", False, str(exc))


def verify_store_and_context() -> bool:
    try:
        from backend.news_intelligence.economic_calendar_store import EconomicCalendarStore
        from backend.news_intelligence.forex_factory_adapter import ForexFactoryAdapter
        from backend.news_intelligence.news_window_engine import NewsWindowEngine

        store = EconomicCalendarStore()
        store.clear()
        adapter = ForexFactoryAdapter()
        window_engine = NewsWindowEngine()
        events = [window_engine.apply_windows(event) for event in adapter.normalize_events([cpi_fixture(), nfp_fixture(), pmi_fixture(), low_fixture()])]
        store.upsert_events(events)
        context = window_engine.build_context(store.list_events())
        passed = (
            len(store.list_events()) == 4
            and len(store.upcoming_events()) >= 4
            and context.high_impact_event_active is True
            and context.risk_level == "EXTREME"
            and context.trade_action == "BLOCK"
            and context.simulation_only is True
            and context.live_execution_enabled is False
        )
        return show("Economic calendar store and news risk context work", passed)
    except Exception as exc:
        return show("Economic calendar store and news risk context work", False, str(exc))


def verify_routes_and_strategy_integration() -> bool:
    try:
        from backend.api.news_routes import news_intelligence_service
        from backend.main import app

        news_intelligence_service.calendar_store.clear()
        client = TestClient(app)
        ingest = client.post("/news/forex-factory/ingest", json=[cpi_fixture(), nfp_fixture()])
        calendar = client.get("/news/calendar")
        upcoming = client.get("/news/upcoming-events")
        risk_context = client.get("/news/risk-context")
        signal_response = client.post("/strategy/analyze/xauusd", json={})
        signal_payload = signal_response.json()
        news_context = signal_payload["metadata"]["news_context"]
        passed = (
            ingest.status_code == 200
            and ingest.json()["ingested"] == 2
            and ingest.json()["external_api_calls_enabled"] is False
            and calendar.status_code == 200
            and len(calendar.json()) == 2
            and upcoming.status_code == 200
            and risk_context.status_code == 200
            and risk_context.json()["trade_action"] == "BLOCK"
            and signal_response.status_code == 200
            and signal_payload["action"] == "WAIT"
            and signal_payload["execution_allowed"] is False
            and news_context["high_impact_event_active"] is True
            and news_context["risk_level"] == "EXTREME"
            and news_context["trade_action"] == "BLOCK"
            and news_context["upcoming_events_count"] >= 2
            and "news risk" in signal_payload["reason"].lower()
        )
        return show("News routes and strategy BLOCK integration work", passed)
    except Exception as exc:
        return show("News routes and strategy BLOCK integration work", False, str(exc))


def verify_no_external_api_calls() -> bool:
    forbidden = ["requests.", "httpx.", "aiohttp", "urllib.request", "BeautifulSoup", "selenium"]
    offenders = []
    for path in (PROJECT_ROOT / "backend/news_intelligence").rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in forbidden:
            if token in text:
                offenders.append(f"{path.relative_to(PROJECT_ROOT).as_posix()}:{token}")
    return show("News intelligence layer contains no external API or scraping calls", not offenders, ", ".join(offenders))


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
        registered_websockets = {
            route.path
            for route in app.routes
            if route.__class__.__name__ == "APIWebSocketRoute"
        }
        all_route_paths = {route.path for route in app.routes}
        expected = {
            "/news/status",
            "/news/supported-sources",
            "/news/supported-events",
            "/news/calendar-placeholder",
            "/news/readiness",
            "/news/forex-factory/ingest",
            "/news/calendar",
            "/news/upcoming-events",
            "/news/risk-context",
            "/strategy/confluence/xauusd",
            "/strategy/regime/xauusd",
        }
        missing = sorted(REQUIRED_GET_ROUTES - registered_get_routes)
        missing += sorted(expected - all_route_paths)
        missing_ws = sorted(REQUIRED_WEBSOCKET_ROUTES - registered_websockets)
        return show("Phase 7 Day 1 and Phase 6 routes are preserved", not missing and not missing_ws, ", ".join(missing + missing_ws))
    except Exception as exc:
        return show("Phase 7 Day 1 and Phase 6 routes are preserved", False, str(exc))


def main() -> int:
    print("Phase 7 Day 2 Forex Factory Calendar Verification")
    print("=" * 60)
    checks = [
        verify_files(),
        verify_models(),
        verify_adapter_and_risk_windows(),
        verify_store_and_context(),
        verify_routes_and_strategy_integration(),
        verify_no_external_api_calls(),
        verify_order_send_isolated(),
        verify_preserved_routes(),
    ]
    print("=" * 60)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
