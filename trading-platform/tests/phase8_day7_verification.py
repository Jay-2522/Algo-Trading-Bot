import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def contexts(direction: str = "BULLISH", no_liquidity: bool = False, no_structure: bool = False, no_entry: bool = False, no_trade_regime: bool = False):
    from backend.strategy_engine.strategy_models import (
        EURUSDFVGContext,
        EURUSDFairValueGap,
        EURUSDLiquidityContext,
        EURUSDOrderBlock,
        EURUSDOrderBlockContext,
        EURUSDRegimeContext,
        EURUSDStructureContext,
        IndicatorContext,
        MarketSessionContext,
    )

    bullish = direction == "BULLISH"
    session = MarketSessionContext(
        current_session="LONDON",
        is_london_session=True,
        is_new_york_session=False,
        is_asian_session=False,
        session_quality="HIGH",
    )
    indicator = IndicatorContext(
        symbol="EURUSD",
        timeframe="H1",
        trend_bias="BULLISH" if bullish else "BEARISH",
        atr=0.001,
        rsi=55.0,
        volatility_state="NORMAL",
        indicator_quality="HIGH",
    )
    liquidity = EURUSDLiquidityContext(
        sweep_direction="NONE" if no_liquidity else ("SELL_SIDE_SWEEP" if bullish else "BUY_SIDE_SWEEP"),
        rejection_detected=not no_liquidity,
        sweep_quality="NONE" if no_liquidity else "HIGH",
        confidence=0.0 if no_liquidity else 90.0,
        active_sweep_level=None if no_liquidity else ("PREVIOUS_DAY_LOW" if bullish else "PREVIOUS_DAY_HIGH"),
    )
    structure = EURUSDStructureContext(
        bos_detected=not no_structure,
        bos_direction="NONE" if no_structure else ("BULLISH_BOS" if bullish else "BEARISH_BOS"),
        choch_direction="NONE",
        post_sweep_confirmation=not no_structure,
        structure_quality="NONE" if no_structure else "HIGH",
        structure_bias="NEUTRAL" if no_structure else direction,
        confidence=0.0 if no_structure else 85.0,
    )
    fvg = EURUSDFVGContext()
    order_block = EURUSDOrderBlockContext()
    if not no_entry:
        fvg_item = EURUSDFairValueGap(
            fvg_id="test-fvg",
            direction=direction,
            start_time="2026-05-30T08:00:00+00:00",
            end_time="2026-05-30T09:00:00+00:00",
            upper_bound=1.082,
            lower_bound=1.081,
            midpoint=1.0815,
            size=0.001,
            quality="HIGH",
            aligned_with_structure=True,
            aligned_with_liquidity=True,
        )
        fvg = EURUSDFVGContext(
            fair_value_gaps=[fvg_item],
            latest_fvg=fvg_item,
            bullish_fvg_detected=bullish,
            bearish_fvg_detected=not bullish,
            active_fvg_detected=True,
            fvg_direction=direction,
            fvg_quality="HIGH",
            fvg_confidence=90.0,
        )
        ob_item = EURUSDOrderBlock(
            order_block_id="test-ob",
            direction=direction,
            creation_time="2026-05-30T08:00:00+00:00",
            upper_bound=1.082,
            lower_bound=1.081,
            midpoint=1.0815,
            fresh=True,
            strength=90.0,
            quality="HIGH",
            aligned_with_structure=True,
            aligned_with_liquidity=True,
            aligned_with_fvg=True,
        )
        order_block = EURUSDOrderBlockContext(
            order_blocks=[ob_item],
            latest_order_block=ob_item,
            bullish_order_block_detected=bullish,
            bearish_order_block_detected=not bullish,
            active_order_block_detected=True,
            order_block_direction=direction,
            order_block_quality="HIGH",
            order_block_confidence=90.0,
        )
    regime = EURUSDRegimeContext(
        regime="UNCLEAR" if no_trade_regime else "TRENDING",
        trend_strength=0.0 if no_trade_regime else 85.0,
        volatility_score=0.0 if no_trade_regime else 10.0,
        range_score=0.0 if no_trade_regime else 20.0,
        atr_state="NORMAL",
        ema_alignment="NEUTRAL" if no_trade_regime else direction,
        session_alignment=True,
        tradeability="AVOID" if no_trade_regime else "HIGH",
        risk_mode="NO_TRADE" if no_trade_regime else "NORMAL",
        confidence=0.0 if no_trade_regime else 90.0,
    )
    news = {
        "high_impact_event_active": False,
        "active_events": [],
        "upcoming_events": [],
        "risk_level": "LOW",
        "trade_action": "ALLOW",
        "reason": "No active news risk window.",
        "simulation_only": True,
        "live_execution_enabled": False,
    }
    macro = {
        "macro_alignment": "ALIGNED",
        "confidence_adjustment": 10.0,
        "reason": "DXY supports EURUSD direction.",
        "simulation_only": True,
        "live_execution_enabled": False,
    }
    return session, indicator, liquidity, structure, fvg, order_block, regime, news, macro


def verify_files_and_models() -> bool:
    files = [
        "backend/strategy_engine/eurusd_confluence_engine.py",
        "backend/strategy_engine/eurusd_reason_builder.py",
        "docs/phase-8-day-7-progress.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    try:
        from backend.strategy_engine.strategy_models import EURUSDConfluenceScore, EURUSDStrategySignal

        expected = {
            "session_score",
            "indicator_score",
            "liquidity_score",
            "structure_score",
            "fvg_score",
            "order_block_score",
            "regime_score",
            "news_score",
            "macro_score",
            "total_score",
            "confidence",
            "trade_quality",
            "aligned_confirmations",
            "missing_confirmations",
            "risk_mode",
            "warnings",
        }
        signal_fields = {
            "news_context",
            "macro_context",
            "confluence_score",
            "trade_quality",
            "aligned_confirmations",
            "missing_confirmations",
            "client_summary",
            "technical_summary",
        }
        model_ok = expected <= set(EURUSDConfluenceScore.model_fields) and signal_fields <= set(EURUSDStrategySignal.model_fields)
    except Exception:
        model_ok = False
    return show("EURUSD confluence files and models exist", not missing and model_ok, ", ".join(missing))


def verify_confluence_engine_and_actions() -> bool:
    try:
        from backend.strategy_engine.eurusd_confluence_engine import EURUSDConfluenceEngine
        from backend.strategy_engine.eurusd_strategy_engine import EURUSDStrategyEngine

        scorer = EURUSDConfluenceEngine()
        engine = EURUSDStrategyEngine()
        bullish_contexts = contexts("BULLISH")
        bearish_contexts = contexts("BEARISH")
        bullish_score = scorer.score(*bullish_contexts)
        bearish_score = scorer.score(*bearish_contexts)
        bullish_signal = engine.generate_signal(*bullish_contexts)
        bearish_signal = engine.generate_signal(*bearish_contexts)
        no_confluence = engine.analyze()
        passed = (
            bullish_score.confidence >= 70
            and bearish_score.confidence >= 70
            and bullish_signal.action == "BUY"
            and bullish_signal.execution_allowed is False
            and bearish_signal.action == "SELL"
            and bearish_signal.execution_allowed is False
            and no_confluence.action == "WAIT"
            and no_confluence.trade_quality == "NO_TRADE"
            and no_confluence.confidence <= 40
        )
        return show("No-confluence, strong bullish, and strong bearish EURUSD confluence work", passed)
    except Exception as exc:
        return show("No-confluence, strong bullish, and strong bearish EURUSD confluence work", False, str(exc))


def verify_caps_and_blocks() -> bool:
    try:
        from backend.strategy_engine.eurusd_confluence_engine import EURUSDConfluenceEngine
        from backend.strategy_engine.eurusd_strategy_engine import EURUSDStrategyEngine

        scorer = EURUSDConfluenceEngine()
        engine = EURUSDStrategyEngine()
        no_liquidity = scorer.score(*contexts("BULLISH", no_liquidity=True))
        no_structure = scorer.score(*contexts("BULLISH", no_structure=True))
        regime_block = engine.generate_signal(*contexts("BULLISH", no_trade_regime=True))
        blocked_contexts = list(contexts("BULLISH"))
        blocked_contexts[7] = {
            "high_impact_event_active": True,
            "active_events": [{"title": "US CPI", "currency": "USD"}],
            "upcoming_events": [],
            "risk_level": "HIGH",
            "trade_action": "BLOCK",
            "reason": "High-impact USD news active.",
            "simulation_only": True,
            "live_execution_enabled": False,
        }
        news_block = engine.generate_signal(*blocked_contexts)
        passed = (
            no_liquidity.confidence <= 40
            and no_structure.confidence <= 50
            and regime_block.action == "WAIT"
            and regime_block.trade_quality == "NO_TRADE"
            and news_block.action == "WAIT"
            and news_block.confidence == 0.0
            and news_block.trade_quality == "NO_TRADE"
        )
        return show("Confidence caps, regime block, and news block work", passed)
    except Exception as exc:
        return show("Confidence caps, regime block, and news block work", False, str(exc))


def verify_summaries_routes_and_strategy() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        confluence = client.get("/strategy/eurusd/confluence")
        signal = client.get("/strategy/analyze/eurusd")
        payload = signal.json()
        confluence_payload = confluence.json()
        passed = (
            confluence.status_code == 200
            and "confluence_score" in confluence_payload
            and "client_summary" in confluence_payload
            and "technical_summary" in confluence_payload
            and signal.status_code == 200
            and "confluence_score" in payload
            and payload["execution_allowed"] is False
            and payload["metadata"]["phase"] == "PHASE_8_DAY_7"
            and payload["metadata"]["confluence_engine_integrated"] is True
            and payload["metadata"]["simulation_only"] is True
            and payload["metadata"]["live_execution_enabled"] is False
            and payload["client_summary"]
            and payload["technical_summary"]
        )
        return show("EURUSD confluence route, strategy integration, client summary, and technical summary work", passed)
    except Exception as exc:
        return show("EURUSD confluence route, strategy integration, client summary, and technical summary work", False, str(exc))


def verify_no_order_send_added() -> bool:
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
        expected = {
            "/strategy/analyze/eurusd",
            "/strategy/eurusd/session-context",
            "/strategy/eurusd/indicator-context",
            "/strategy/eurusd/liquidity",
            "/strategy/eurusd/structure",
            "/strategy/eurusd/fvg",
            "/strategy/eurusd/order-block",
            "/strategy/eurusd/regime",
            "/strategy/eurusd/confluence",
            "/strategy/confluence/xauusd",
            "/strategy/order-block/xauusd",
            "/strategy/regime/xauusd",
            "/news/phase7/status",
            "/news/command-center",
        }
        missing = sorted((REQUIRED_GET_ROUTES | expected) - registered_get_routes)
        missing_ws = sorted(REQUIRED_WEBSOCKET_ROUTES - registered_websockets)
        return show("Phase 8 Day 1-6, XAUUSD, and Phase 7 routes are preserved", not missing and not missing_ws, ", ".join(missing + missing_ws))
    except Exception as exc:
        return show("Phase 8 Day 1-6, XAUUSD, and Phase 7 routes are preserved", False, str(exc))


def main() -> int:
    print("Phase 8 Day 7 EURUSD Confluence Verification")
    print("=" * 58)
    checks = [
        verify_files_and_models(),
        verify_confluence_engine_and_actions(),
        verify_caps_and_blocks(),
        verify_summaries_routes_and_strategy(),
        verify_no_order_send_added(),
        verify_preserved_routes(),
    ]
    print("=" * 58)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
