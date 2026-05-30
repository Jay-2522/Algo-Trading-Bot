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
        "backend/news_intelligence/macro_models.py",
        "backend/news_intelligence/macro_bias_engine.py",
        "backend/news_intelligence/macro_context_store.py",
        "backend/news_intelligence/macro_strategy_filter.py",
        "docs/phase-7-day-4-progress.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    return show("Macro models, engine, store, filter, and docs exist", not missing, ", ".join(missing))


def verify_macro_bias_rules() -> bool:
    try:
        from backend.news_intelligence.macro_bias_engine import MacroBiasEngine

        engine = MacroBiasEngine()
        dxy_down = engine.build_instrument_context("DXY", 104.10, 104.70)
        us10y_down = engine.build_instrument_context("US10Y", 4.21, 4.30)
        dxy_up = engine.build_instrument_context("DXY", 105.20, 104.70)
        us10y_up = engine.build_instrument_context("US10Y", 4.40, 4.30)
        bullish = engine.build_xauusd_macro_bias(dxy_down, us10y_down)
        bearish = engine.build_xauusd_macro_bias(dxy_up, us10y_up)
        mixed = engine.build_xauusd_macro_bias(dxy_up, us10y_down)
        unknown = engine.build_xauusd_macro_bias(dxy_down, None)
        passed = (
            dxy_down.direction == "DOWN"
            and dxy_down.momentum in {"MODERATE", "STRONG"}
            and us10y_down.direction == "DOWN"
            and bullish.gold_bias == "BULLISH"
            and bearish.gold_bias == "BEARISH"
            and mixed.gold_bias == "MIXED"
            and unknown.gold_bias == "UNKNOWN"
        )
        return show("DXY/US10Y macro bias rules work", passed)
    except Exception as exc:
        return show("DXY/US10Y macro bias rules work", False, str(exc))


def verify_macro_strategy_filter_and_confluence() -> bool:
    try:
        from backend.news_intelligence.macro_bias_engine import MacroBiasEngine
        from backend.news_intelligence.macro_strategy_filter import MacroStrategyFilter
        from backend.strategy_engine.confluence_score_engine import ConfluenceScoreEngine
        from tests.phase6_day7_verification import indicator_context, liquidity_context, regime_context, session_context, smc_context

        engine = MacroBiasEngine()
        bullish = engine.build_xauusd_macro_bias(
            engine.build_instrument_context("DXY", 104.10, 104.70),
            engine.build_instrument_context("US10Y", 4.21, 4.30),
        )
        bearish = engine.build_xauusd_macro_bias(
            engine.build_instrument_context("DXY", 105.20, 104.70),
            engine.build_instrument_context("US10Y", 4.40, 4.30),
        )
        aligned = MacroStrategyFilter().evaluate_xauusd("BUY", bullish)
        conflicting = MacroStrategyFilter().evaluate_xauusd("BUY", bearish)
        base = ConfluenceScoreEngine().score(session_context(), indicator_context(), liquidity_context(), smc_context(), regime_context())
        aligned_score = ConfluenceScoreEngine().score(session_context(), indicator_context(), liquidity_context(), smc_context(), regime_context(), macro_context=aligned)
        conflict_score = ConfluenceScoreEngine().score(session_context(), indicator_context(), liquidity_context(), smc_context(), regime_context(), macro_context=conflicting)
        passed = (
            aligned.macro_alignment == "ALIGNED"
            and aligned.confidence_adjustment == 10
            and conflicting.macro_alignment == "CONFLICTING"
            and conflicting.confidence_adjustment == -20
            and aligned_score.confidence >= base.confidence
            and conflict_score.confidence < base.confidence
            and conflict_score.risk_mode == "REDUCED_RISK"
        )
        return show("Macro strategy filter and confluence confidence adjustment work", passed)
    except Exception as exc:
        return show("Macro strategy filter and confluence confidence adjustment work", False, str(exc))


def verify_macro_routes_and_strategy() -> bool:
    try:
        from backend.api.news_routes import news_intelligence_service
        from backend.main import app

        news_intelligence_service.macro_context_store.clear()
        client = TestClient(app)
        status = client.get("/news/macro/status")
        dxy = client.post("/news/macro/context", json={"symbol": "DXY", "current_value": 104.10, "previous_value": 104.70})
        us10y = client.post("/news/macro/context", json={"symbol": "US10Y", "current_value": 4.21, "previous_value": 4.30})
        contexts = client.get("/news/macro/context")
        bias = client.get("/news/macro/xauusd-bias")
        evaluated = client.post("/news/macro/xauusd-bias/evaluate", json={"action": "BUY"})
        signal = client.post("/strategy/analyze/xauusd", json={})
        payload = signal.json()
        passed = (
            status.status_code == 200
            and status.json()["simulation_only"] is True
            and status.json()["live_execution_enabled"] is False
            and dxy.status_code == 200
            and dxy.json()["direction"] == "DOWN"
            and us10y.status_code == 200
            and us10y.json()["direction"] == "DOWN"
            and contexts.status_code == 200
            and len(contexts.json()) == 2
            and bias.status_code == 200
            and bias.json()["gold_bias"] == "BULLISH"
            and evaluated.status_code == 200
            and evaluated.json()["macro_alignment"] == "ALIGNED"
            and evaluated.json()["confidence_adjustment"] == 10
            and signal.status_code == 200
            and "macro_context" in payload["metadata"]
            and "macro_alignment" in payload["metadata"]
            and "macro_confidence_adjustment" in payload["metadata"]
            and payload["execution_allowed"] is False
            and payload["metadata"]["simulation_only"] is True
            and payload["metadata"]["live_execution_enabled"] is False
        )
        return show("Macro routes and XAUUSD strategy metadata integration work", passed)
    except Exception as exc:
        return show("Macro routes and XAUUSD strategy metadata integration work", False, str(exc))


def verify_no_external_api_calls() -> bool:
    forbidden = ["requests.", "httpx.", "aiohttp", "urllib.request", "BeautifulSoup", "selenium"]
    offenders = []
    for path in (PROJECT_ROOT / "backend/news_intelligence").rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in forbidden:
            if token in text:
                offenders.append(f"{path.relative_to(PROJECT_ROOT).as_posix()}:{token}")
    return show("News intelligence macro layer contains no external API or scraping calls", not offenders, ", ".join(offenders))


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
            "/news/filter/current/xauusd",
            "/news/macro/status",
            "/news/macro/context",
            "/news/macro/xauusd-bias",
            "/news/macro/xauusd-bias/evaluate",
            "/strategy/confluence/xauusd",
            "/strategy/regime/xauusd",
        }
        missing = sorted(REQUIRED_GET_ROUTES - registered_get_routes)
        missing += sorted(expected - all_route_paths)
        missing_ws = sorted(REQUIRED_WEBSOCKET_ROUTES - registered_websockets)
        return show("Phase 7 Day 1-3 and Phase 6 routes are preserved", not missing and not missing_ws, ", ".join(missing + missing_ws))
    except Exception as exc:
        return show("Phase 7 Day 1-3 and Phase 6 routes are preserved", False, str(exc))


def main() -> int:
    print("Phase 7 Day 4 DXY / US10Y Macro Bias Verification")
    print("=" * 60)
    checks = [
        verify_files(),
        verify_macro_bias_rules(),
        verify_macro_strategy_filter_and_confluence(),
        verify_macro_routes_and_strategy(),
        verify_no_external_api_calls(),
        verify_order_send_isolated(),
        verify_preserved_routes(),
    ]
    print("=" * 60)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
