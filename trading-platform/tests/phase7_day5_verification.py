import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def hawkish_powell_payload() -> list[dict]:
    return [
        {
            "title": "FED'S POWELL SAYS INFLATION REMAINS TOO HIGH",
            "body": "",
            "timestamp": "2026-05-30T14:00:00Z",
            "source": "Financial Juice",
        }
    ]


def verify_files_and_models() -> bool:
    files = [
        "backend/news_intelligence/headline_models.py",
        "backend/news_intelligence/financial_juice_adapter.py",
        "backend/news_intelligence/headline_classifier.py",
        "backend/news_intelligence/headline_risk_engine.py",
        "backend/news_intelligence/headline_store.py",
        "backend/news_intelligence/headline_strategy_filter.py",
        "docs/phase-7-day-5-progress.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    try:
        from backend.news_intelligence.headline_models import HeadlineEvent, HeadlineRiskContext

        model_ok = "headline_id" in HeadlineEvent.model_fields and "headline_trade_action" in HeadlineRiskContext.model_fields
    except Exception:
        model_ok = False
    return show("Headline files and models exist", not missing and model_ok, ", ".join(missing))


def verify_classifier_and_adapter() -> bool:
    try:
        from backend.news_intelligence.financial_juice_adapter import FinancialJuiceAdapter

        adapter = FinancialJuiceAdapter()
        powell = adapter.normalize_headline(hawkish_powell_payload()[0])
        war = adapter.normalize_headline({"title": "WAR ESCALATION SENDS SAFE HAVEN GOLD HIGHER", "source": "Financial Juice"})
        fomc = adapter.normalize_headline({"title": "FOMC SURPRISE RATE DECISION SHOCKS MARKET", "source": "Financial Juice"})
        unrelated = adapter.normalize_headline({"title": "Large technology company announces new laptop", "source": "Financial Juice"})
        passed = (
            powell.source == "FINANCIAL_JUICE"
            and "FED" in powell.categories
            and "INFLATION" in powell.categories
            and powell.risk_level == "HIGH"
            and powell.sentiment in {"BEARISH_GOLD", "MIXED"}
            and "GEOPOLITICAL" in war.categories
            and war.sentiment == "BULLISH_GOLD"
            and war.risk_level in {"HIGH", "EXTREME"}
            and fomc.risk_level == "EXTREME"
            and unrelated.risk_level == "LOW"
            and unrelated.active is False
        )
        return show("Financial Juice adapter and headline classifier work", passed)
    except Exception as exc:
        return show("Financial Juice adapter and headline classifier work", False, str(exc))


def verify_risk_context_and_filter() -> bool:
    try:
        from backend.news_intelligence.financial_juice_adapter import FinancialJuiceAdapter
        from backend.news_intelligence.headline_risk_engine import HeadlineRiskEngine
        from backend.news_intelligence.headline_strategy_filter import HeadlineStrategyFilter
        from backend.strategy_engine.confluence_score_engine import ConfluenceScoreEngine
        from tests.phase6_day7_verification import indicator_context, liquidity_context, regime_context, session_context, smc_context

        adapter = FinancialJuiceAdapter()
        engine = HeadlineRiskEngine()
        context = engine.build_context(adapter.normalize_headlines(hawkish_powell_payload()))
        decision = HeadlineStrategyFilter().evaluate_xauusd("BUY", context)
        fomc_context = engine.build_context(adapter.normalize_headlines([{"title": "FOMC SURPRISE RATE DECISION SHOCKS MARKET"}]))
        block = HeadlineStrategyFilter().evaluate_xauusd("BUY", fomc_context)
        base = ConfluenceScoreEngine().score(session_context(), indicator_context(), liquidity_context(), smc_context(), regime_context())
        reduced = ConfluenceScoreEngine().score(
            session_context(),
            indicator_context(),
            liquidity_context(),
            smc_context(),
            regime_context(),
            headline_filter_decision=decision,
        )
        blocked = ConfluenceScoreEngine().score(
            session_context(),
            indicator_context(),
            liquidity_context(),
            smc_context(),
            regime_context(),
            headline_filter_decision=block,
        )
        passed = (
            context.highest_risk_level == "HIGH"
            and context.headline_trade_action == "WAIT_FOR_CONFIRMATION"
            and decision.confidence_cap == 40
            and fomc_context.headline_trade_action == "BLOCK"
            and block.blocked is True
            and block.confidence_cap == 0
            and reduced.confidence <= 40
            and blocked.confidence == 0
            and blocked.trade_quality == "NO_TRADE"
        )
        return show("Headline risk context, filter, and confluence adjustment work", passed)
    except Exception as exc:
        return show("Headline risk context, filter, and confluence adjustment work", False, str(exc))


def verify_routes_and_strategy() -> bool:
    try:
        from backend.api.news_routes import news_intelligence_service
        from backend.main import app

        news_intelligence_service.headline_store.clear()
        client = TestClient(app)
        ingest = client.post("/news/headlines/ingest", json=hawkish_powell_payload())
        headlines = client.get("/news/headlines")
        recent = client.get("/news/headlines/recent")
        context = client.get("/news/headlines/risk-context")
        evaluate = client.post("/news/headlines/evaluate", json={"action": "BUY"})
        signal = client.post("/strategy/analyze/xauusd", json={})

        news_intelligence_service.headline_store.clear()
        client.post("/news/headlines/ingest", json=[{"title": "FOMC SURPRISE RATE DECISION SHOCKS MARKET", "source": "Financial Juice"}])
        blocked_signal = client.post("/strategy/analyze/xauusd", json={})
        payload = signal.json()
        blocked_payload = blocked_signal.json()
        passed = (
            ingest.status_code == 200
            and ingest.json()["simulation_only"] is True
            and ingest.json()["external_api_calls_enabled"] is False
            and headlines.status_code == 200
            and len(headlines.json()) >= 1
            and recent.status_code == 200
            and context.status_code == 200
            and context.json()["headline_trade_action"] in {"WAIT_FOR_CONFIRMATION", "REDUCE_RISK"}
            and evaluate.status_code == 200
            and evaluate.json()["trade_action"] in {"WAIT_FOR_CONFIRMATION", "REDUCE_RISK"}
            and signal.status_code == 200
            and "headline_context" in payload["metadata"]
            and "headline_filter_decision" in payload["metadata"]
            and payload["execution_allowed"] is False
            and blocked_signal.status_code == 200
            and blocked_payload["action"] == "WAIT"
            and blocked_payload["metadata"]["headline_filter_decision"]["blocked"] is True
            and blocked_payload["metadata"]["simulation_only"] is True
            and blocked_payload["metadata"]["live_execution_enabled"] is False
        )
        news_intelligence_service.headline_store.clear()
        return show("Headline routes and strategy metadata integration work", passed)
    except Exception as exc:
        return show("Headline routes and strategy metadata integration work", False, str(exc))


def verify_no_external_api_calls() -> bool:
    forbidden = ["requests.", "httpx.", "aiohttp", "urllib.request", "BeautifulSoup", "selenium"]
    offenders = []
    for path in (PROJECT_ROOT / "backend/news_intelligence").rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in forbidden:
            if token in text:
                offenders.append(f"{path.relative_to(PROJECT_ROOT).as_posix()}:{token}")
    return show("News intelligence headline layer contains no external API or scraping calls", not offenders, ", ".join(offenders))


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
            "/news/risk-context",
            "/news/macro/xauusd-bias",
            "/news/headlines",
            "/news/headlines/recent",
            "/news/headlines/risk-context",
            "/news/headlines/evaluate",
            "/strategy/confluence/xauusd",
            "/strategy/regime/xauusd",
        }
        missing = sorted(REQUIRED_GET_ROUTES - registered_get_routes)
        missing += sorted(expected - all_route_paths)
        missing_ws = sorted(REQUIRED_WEBSOCKET_ROUTES - registered_websockets)
        return show("Phase 7 Day 1-4 and Phase 6 routes are preserved", not missing and not missing_ws, ", ".join(missing + missing_ws))
    except Exception as exc:
        return show("Phase 7 Day 1-4 and Phase 6 routes are preserved", False, str(exc))


def main() -> int:
    print("Phase 7 Day 5 Financial Juice / Headline Intelligence Verification")
    print("=" * 72)
    checks = [
        verify_files_and_models(),
        verify_classifier_and_adapter(),
        verify_risk_context_and_filter(),
        verify_routes_and_strategy(),
        verify_no_external_api_calls(),
        verify_order_send_isolated(),
        verify_preserved_routes(),
    ]
    print("=" * 72)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
