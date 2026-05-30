import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def event(title: str, risk: str, minutes_until: int | None = None, currency: str = "USD", trade_action: str = "BLOCK") -> dict:
    data = {
        "title": title,
        "currency": currency,
        "impact": "HIGH" if risk in {"HIGH", "EXTREME"} else risk,
        "risk_level": risk,
        "trade_action": trade_action,
    }
    if minutes_until is not None:
        data["minutes_until"] = minutes_until
    return data


def news_context(active=None, upcoming=None, risk="LOW", action="ALLOW") -> dict:
    return {
        "high_impact_event_active": bool(active),
        "active_events": active or [],
        "upcoming_events": upcoming or [],
        "risk_level": risk,
        "trade_action": action,
        "reason": "Fixture news context.",
    }


def verify_files_and_model() -> bool:
    files = [
        "backend/news_intelligence/news_filter_models.py",
        "backend/news_intelligence/news_strategy_filter.py",
        "backend/news_intelligence/news_block_reason_builder.py",
        "docs/phase-7-day-3-progress.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    if missing:
        return show("News filter files and docs exist", False, ", ".join(missing))
    try:
        from backend.news_intelligence.news_filter_models import NewsFilterDecision

        expected = {
            "decision_id",
            "symbol",
            "blocked",
            "confidence_cap",
            "confidence_penalty",
            "risk_level",
            "trade_action",
            "active_events",
            "upcoming_events",
            "reason",
            "client_message",
            "technical_message",
            "simulation_only",
            "live_execution_enabled",
            "timestamp",
        }
        return show("NewsFilterDecision model exists", expected <= set(NewsFilterDecision.model_fields))
    except Exception as exc:
        return show("NewsFilterDecision model exists", False, str(exc))


def verify_filter_rules() -> bool:
    try:
        from backend.news_intelligence.news_strategy_filter import NewsStrategyFilter

        strategy_filter = NewsStrategyFilter()
        active_high = strategy_filter.evaluate(news_context=news_context(active=[event("Core CPI m/m", "HIGH")], risk="HIGH", action="BLOCK"))
        active_extreme = strategy_filter.evaluate(news_context=news_context(active=[event("FOMC Rate Decision", "EXTREME")], risk="EXTREME", action="BLOCK"))
        upcoming_nfp = strategy_filter.evaluate(news_context=news_context(upcoming=[event("Non-Farm Employment Change", "EXTREME", 45)], risk="EXTREME", action="BLOCK"))
        medium = strategy_filter.evaluate(news_context=news_context(upcoming=[event("Flash PMI", "MEDIUM", 10, currency="EUR", trade_action="REDUCE_RISK")], risk="MEDIUM", action="REDUCE_RISK"))
        no_event = strategy_filter.evaluate(news_context=news_context())
        past_time = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        stabilization = strategy_filter.evaluate(
            news_context=news_context(
                active=[
                    {
                        **event("Core CPI m/m", "HIGH"),
                        "scheduled_time": past_time,
                    }
                ],
                risk="HIGH",
                action="BLOCK",
            )
        )
        passed = (
            active_high.blocked is True
            and active_high.confidence_cap <= 20
            and active_high.trade_action == "BLOCK"
            and active_extreme.blocked is True
            and active_extreme.confidence_cap == 0
            and upcoming_nfp.blocked is True
            and upcoming_nfp.confidence_cap == 0
            and medium.blocked is False
            and medium.trade_action == "REDUCE_RISK"
            and medium.confidence_penalty == 20
            and no_event.blocked is False
            and no_event.trade_action == "ALLOW"
            and stabilization.blocked is True
            and stabilization.trade_action == "WAIT_FOR_STABILIZATION"
            and stabilization.confidence_cap == 30
        )
        return show("News strategy filter blocking, reduction, allow, and stabilization rules work", passed)
    except Exception as exc:
        return show("News strategy filter blocking, reduction, allow, and stabilization rules work", False, str(exc))


def verify_confluence_news_adjustment() -> bool:
    try:
        from backend.news_intelligence.news_strategy_filter import NewsStrategyFilter
        from backend.strategy_engine.confluence_score_engine import ConfluenceScoreEngine
        from tests.phase6_day7_verification import indicator_context, liquidity_context, regime_context, session_context, smc_context

        blocked = NewsStrategyFilter().evaluate(
            news_context=news_context(active=[event("Core CPI m/m", "HIGH")], risk="HIGH", action="BLOCK")
        )
        reduced = NewsStrategyFilter().evaluate(
            news_context=news_context(upcoming=[event("Flash PMI", "MEDIUM", 10, trade_action="REDUCE_RISK")], risk="MEDIUM", action="REDUCE_RISK")
        )
        engine = ConfluenceScoreEngine()
        blocked_score = engine.score(session_context(), indicator_context(), liquidity_context(), smc_context(), regime_context(), blocked)
        reduced_score = engine.score(session_context(), indicator_context(), liquidity_context(), smc_context(), regime_context(), reduced)
        passed = (
            blocked_score.confidence <= 20
            and blocked_score.trade_quality == "NO_TRADE"
            and blocked_score.risk_mode == "NO_TRADE"
            and reduced_score.risk_mode == "REDUCED_RISK"
            and reduced_score.confidence < 100
        )
        return show("Confluence engine applies news confidence cap and penalty", passed)
    except Exception as exc:
        return show("Confluence engine applies news confidence cap and penalty", False, str(exc))


def verify_routes_and_strategy_block() -> bool:
    try:
        from backend.api.news_routes import news_intelligence_service
        from backend.main import app

        news_intelligence_service.calendar_store.clear()
        client = TestClient(app)
        ingest = client.post(
            "/news/forex-factory/ingest",
            json=[
                {
                    "title": "Core CPI m/m",
                    "currency": "USD",
                    "impact": "High",
                    "time": (datetime.now(timezone.utc) + timedelta(minutes=20)).isoformat().replace("+00:00", "Z"),
                    "forecast": "0.3%",
                    "previous": "0.2%",
                }
            ],
        )
        evaluate = client.post(
            "/news/filter/evaluate",
            json={"symbol": "XAUUSD", "news_context": news_context(active=[event("Core CPI m/m", "HIGH")], risk="HIGH", action="BLOCK")},
        )
        current = client.get("/news/filter/current/xauusd")
        status = client.get("/news/filter/status")
        signal = client.post("/strategy/analyze/xauusd", json={})
        payload = signal.json()
        decision = payload["metadata"]["news_filter_decision"]
        passed = (
            ingest.status_code == 200
            and evaluate.status_code == 200
            and evaluate.json()["blocked"] is True
            and current.status_code == 200
            and current.json()["blocked"] is True
            and status.status_code == 200
            and status.json()["simulation_only"] is True
            and status.json()["live_execution_enabled"] is False
            and signal.status_code == 200
            and payload["action"] == "WAIT"
            and payload["execution_allowed"] is False
            and decision["blocked"] is True
            and decision["trade_action"] == "BLOCK"
        )
        return show("News filter routes work and news block forces strategy WAIT", passed)
    except Exception as exc:
        return show("News filter routes work and news block forces strategy WAIT", False, str(exc))


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
            "/news/risk-context",
            "/news/calendar",
            "/news/upcoming-events",
            "/news/filter/status",
            "/news/filter/evaluate",
            "/news/filter/current/xauusd",
            "/strategy/confluence/xauusd",
            "/strategy/regime/xauusd",
        }
        missing = sorted(REQUIRED_GET_ROUTES - registered_get_routes)
        missing += sorted(expected - all_route_paths)
        missing_ws = sorted(REQUIRED_WEBSOCKET_ROUTES - registered_websockets)
        return show("Phase 7 Day 1-2 and Phase 6 routes are preserved", not missing and not missing_ws, ", ".join(missing + missing_ws))
    except Exception as exc:
        return show("Phase 7 Day 1-2 and Phase 6 routes are preserved", False, str(exc))


def main() -> int:
    print("Phase 7 Day 3 News Risk Filter Verification")
    print("=" * 54)
    checks = [
        verify_files_and_model(),
        verify_filter_rules(),
        verify_confluence_news_adjustment(),
        verify_routes_and_strategy_block(),
        verify_no_external_api_calls(),
        verify_order_send_isolated(),
        verify_preserved_routes(),
    ]
    print("=" * 54)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
