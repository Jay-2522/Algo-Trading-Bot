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
        "backend/news_intelligence/unified_news_models.py",
        "backend/news_intelligence/unified_news_orchestrator.py",
        "backend/news_intelligence/news_confidence_adjuster.py",
        "docs/phase-7-day-6-progress.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    try:
        from backend.news_intelligence.unified_news_models import UnifiedNewsRiskDecision

        model_ok = (
            "decision_id" in UnifiedNewsRiskDecision.model_fields
            and "final_trade_action" in UnifiedNewsRiskDecision.model_fields
            and "confidence_cap" in UnifiedNewsRiskDecision.model_fields
        )
    except Exception:
        model_ok = False
    return show("Unified news files and model exist", not missing and model_ok, ", ".join(missing))


def verify_orchestrator_rules() -> bool:
    try:
        from backend.news_intelligence.unified_news_orchestrator import UnifiedNewsOrchestrator

        orchestrator = UnifiedNewsOrchestrator()
        extreme_calendar = orchestrator.evaluate_xauusd(calendar_context={"risk_level": "EXTREME", "trade_action": "BLOCK", "high_impact_event_active": True})
        high_calendar = orchestrator.evaluate_xauusd(calendar_context={"risk_level": "HIGH", "trade_action": "BLOCK", "high_impact_event_active": True})
        headline_block = orchestrator.evaluate_xauusd(headline_context={"highest_risk_level": "EXTREME", "headline_trade_action": "BLOCK"})
        macro_conflict = orchestrator.evaluate_xauusd(macro_context={"macro_risk_level": "HIGH", "macro_alignment": "CONFLICTING"})
        all_clear = orchestrator.evaluate_xauusd()
        passed = (
            extreme_calendar.final_trade_action == "BLOCK"
            and extreme_calendar.final_risk_level == "EXTREME"
            and extreme_calendar.confidence_cap == 0
            and high_calendar.final_trade_action == "BLOCK"
            and high_calendar.confidence_cap <= 20
            and headline_block.final_trade_action == "BLOCK"
            and headline_block.confidence_cap == 0
            and macro_conflict.final_trade_action == "REDUCE_RISK"
            and macro_conflict.confidence_adjustment == -20
            and all_clear.final_trade_action == "ALLOW"
            and all_clear.final_risk_level == "LOW"
        )
        return show("Unified news orchestrator priority rules work", passed)
    except Exception as exc:
        return show("Unified news orchestrator priority rules work", False, str(exc))


def verify_confidence_adjuster_and_confluence() -> bool:
    try:
        from backend.news_intelligence.news_confidence_adjuster import NewsConfidenceAdjuster
        from backend.news_intelligence.unified_news_orchestrator import UnifiedNewsOrchestrator
        from backend.strategy_engine.confluence_score_engine import ConfluenceScoreEngine
        from tests.phase6_day7_verification import indicator_context, liquidity_context, regime_context, session_context, smc_context

        adjuster = NewsConfidenceAdjuster()
        orchestrator = UnifiedNewsOrchestrator()
        block = orchestrator.evaluate_xauusd(headline_context={"highest_risk_level": "EXTREME", "headline_trade_action": "BLOCK"})
        reduce = orchestrator.evaluate_xauusd(macro_context={"macro_alignment": "CONFLICTING", "macro_risk_level": "HIGH"})
        allow_support = orchestrator.evaluate_xauusd(macro_context={"macro_alignment": "ALIGNED", "macro_risk_level": "LOW"})
        base_confidence = 80.0
        confluence = ConfluenceScoreEngine().score(
            session_context(),
            indicator_context(),
            liquidity_context(),
            smc_context(),
            regime_context(),
            unified_news_decision=block,
        )
        passed = (
            adjuster.apply(base_confidence, block) == 0
            and adjuster.apply(base_confidence, reduce) == 60
            and adjuster.apply(98, allow_support) == 100
            and confluence.confidence == 0
            and confluence.trade_quality == "NO_TRADE"
            and confluence.risk_mode == "NO_TRADE"
        )
        return show("News confidence adjuster and confluence unified adjustment work", passed)
    except Exception as exc:
        return show("News confidence adjuster and confluence unified adjustment work", False, str(exc))


def verify_routes_and_strategy() -> bool:
    try:
        from backend.api.news_routes import news_intelligence_service
        from backend.main import app

        news_intelligence_service.calendar_store.clear()
        news_intelligence_service.headline_store.clear()
        client = TestClient(app)
        status = client.get("/news/unified-risk/status")
        all_clear = client.get("/news/unified-risk/xauusd")
        explicit = client.post(
            "/news/unified-risk/evaluate",
            json={"headline_context": {"highest_risk_level": "EXTREME", "headline_trade_action": "BLOCK"}},
        )
        client.post("/news/headlines/ingest", json=[{"title": "FOMC SURPRISE RATE DECISION SHOCKS MARKET", "source": "Financial Juice"}])
        signal = client.post("/strategy/analyze/xauusd", json={})
        payload = signal.json()
        passed = (
            status.status_code == 200
            and status.json()["simulation_only"] is True
            and status.json()["live_execution_enabled"] is False
            and all_clear.status_code == 200
            and all_clear.json()["final_trade_action"] == "ALLOW"
            and explicit.status_code == 200
            and explicit.json()["final_trade_action"] == "BLOCK"
            and explicit.json()["confidence_cap"] == 0
            and signal.status_code == 200
            and "unified_news_decision" in payload["metadata"]
            and payload["metadata"]["unified_news_decision"]["final_trade_action"] == "BLOCK"
            and payload["action"] == "WAIT"
            and payload["execution_allowed"] is False
            and payload["metadata"]["simulation_only"] is True
            and payload["metadata"]["live_execution_enabled"] is False
        )
        news_intelligence_service.headline_store.clear()
        return show("Unified risk routes and strategy integration work", passed)
    except Exception as exc:
        return show("Unified risk routes and strategy integration work", False, str(exc))


def verify_no_external_api_calls() -> bool:
    forbidden = ["requests.", "httpx.", "aiohttp", "urllib.request", "BeautifulSoup", "selenium"]
    offenders = []
    for path in (PROJECT_ROOT / "backend/news_intelligence").rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in forbidden:
            if token in text:
                offenders.append(f"{path.relative_to(PROJECT_ROOT).as_posix()}:{token}")
    return show("News intelligence unified layer contains no external API or scraping calls", not offenders, ", ".join(offenders))


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
            "/news/headlines/risk-context",
            "/news/unified-risk/status",
            "/news/unified-risk/xauusd",
            "/news/unified-risk/evaluate",
            "/strategy/confluence/xauusd",
            "/strategy/regime/xauusd",
        }
        missing = sorted(REQUIRED_GET_ROUTES - registered_get_routes)
        missing += sorted(expected - all_route_paths)
        missing_ws = sorted(REQUIRED_WEBSOCKET_ROUTES - registered_websockets)
        return show("Phase 7 Day 1-5 and Phase 6 routes are preserved", not missing and not missing_ws, ", ".join(missing + missing_ws))
    except Exception as exc:
        return show("Phase 7 Day 1-5 and Phase 6 routes are preserved", False, str(exc))


def main() -> int:
    print("Phase 7 Day 6 Unified News Risk Orchestrator Verification")
    print("=" * 66)
    checks = [
        verify_files_and_model(),
        verify_orchestrator_rules(),
        verify_confidence_adjuster_and_confluence(),
        verify_routes_and_strategy(),
        verify_no_external_api_calls(),
        verify_order_send_isolated(),
        verify_preserved_routes(),
    ]
    print("=" * 66)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
