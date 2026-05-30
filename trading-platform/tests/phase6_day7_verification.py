import sys
from pathlib import Path

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def show(name: str, passed: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if passed else 'FAIL'}] {name}{' - ' + detail if detail else ''}")
    return passed


def session_context(quality: str = "HIGH"):
    from backend.strategy_engine.strategy_models import MarketSessionContext

    return MarketSessionContext(
        current_session="LONDON" if quality == "HIGH" else "OFF_SESSION",
        is_london_session=quality == "HIGH",
        is_new_york_session=False,
        is_asian_session=False,
        session_quality=quality,
    )


def indicator_context():
    from backend.strategy_engine.strategy_models import IndicatorContext

    return IndicatorContext(
        symbol="XAUUSD",
        timeframe="H1",
        ema_50=2320,
        ema_200=2300,
        trend_bias="BULLISH",
        atr=4.5,
        rsi=55,
        volatility_state="NORMAL",
        indicator_quality="HIGH",
    )


def liquidity_context(direction: str = "SELL_SIDE_SWEEP", quality: str = "HIGH"):
    from backend.strategy_engine.strategy_models import LiquiditySweepContext

    return LiquiditySweepContext(
        symbol="XAUUSD",
        sweep_direction=direction,
        rejection_detected=direction != "NONE",
        sweep_quality=quality,
        confidence=90.0 if direction != "NONE" else 0.0,
    )


def smc_context(direction: str = "BULLISH", with_structure: bool = True, with_entry_zone: bool = True):
    from backend.strategy_engine.strategy_models import FairValueGap, OrderBlock, SMCStructureContext

    fvg = None
    order_block = None
    if with_entry_zone:
        fvg = FairValueGap(
            fvg_id="test-fvg",
            symbol="XAUUSD",
            direction=direction,
            start_time="2026-01-02T07:00:00+00:00",
            end_time="2026-01-02T08:00:00+00:00",
            upper_bound=2330,
            lower_bound=2325,
            midpoint=2327.5,
            size=5,
            active=True,
            quality="HIGH",
            aligned_with_structure=True,
            aligned_with_liquidity=True,
        )
        order_block = OrderBlock(
            order_block_id="test-ob",
            symbol="XAUUSD",
            direction=direction,
            creation_time="2026-01-02T07:00:00+00:00",
            upper_bound=2328,
            lower_bound=2322,
            midpoint=2325,
            active=True,
            fresh=True,
            strength=90,
            quality="HIGH",
            aligned_with_structure=True,
            aligned_with_liquidity=True,
            aligned_with_fvg=True,
        )
    bullish = direction == "BULLISH"
    return SMCStructureContext(
        symbol="XAUUSD",
        bos_detected=with_structure,
        bos_direction=("BULLISH_BOS" if bullish else "BEARISH_BOS") if with_structure else "NONE",
        choch_direction="NONE",
        structure_shift_detected=with_structure,
        post_sweep_confirmation=with_structure,
        structure_quality="HIGH" if with_structure else "NONE",
        structure_bias=direction if with_structure else "NEUTRAL",
        confidence=90 if with_structure else 0,
        fair_value_gaps=[fvg] if fvg else [],
        latest_fvg=fvg,
        active_fvg_detected=fvg is not None,
        fvg_direction=direction if fvg else "NONE",
        fvg_quality="HIGH" if fvg else "NONE",
        fvg_confidence=90 if fvg else 0,
        order_blocks=[order_block] if order_block else [],
        latest_order_block=order_block,
        active_order_block_detected=order_block is not None,
        order_block_direction=direction if order_block else "NONE",
        order_block_quality="HIGH" if order_block else "NONE",
        order_block_confidence=90 if order_block else 0,
    )


def regime_context(regime: str = "TRENDING", risk_mode: str = "NORMAL"):
    from backend.strategy_engine.strategy_models import MarketRegimeContext

    return MarketRegimeContext(
        symbol="XAUUSD",
        regime=regime,
        trend_strength=85,
        volatility_score=20,
        range_score=20,
        atr_state="NORMAL",
        ema_alignment="BULLISH",
        session_alignment=True,
        tradeability="HIGH" if risk_mode == "NORMAL" else "AVOID",
        risk_mode=risk_mode,
        confidence=90 if risk_mode == "NORMAL" else 0,
    )


class FakeSessionService:
    def get_session_context(self):
        return session_context()


class FakeIndicatorBuilder:
    def build_context(self, symbol, timeframe, candles):
        return indicator_context()


class FakeLiquidityDetector:
    def __init__(self, direction: str):
        self.direction = direction

    def detect(self, symbol, candles):
        return liquidity_context(self.direction)


class FakeSMCDetector:
    def __init__(self, direction: str):
        self.direction = direction

    def detect(self, symbol, candles, liquidity_context=None, session_context=None):
        return smc_context(self.direction)


class FakeRegimeDetector:
    def __init__(self, risk_mode: str = "NORMAL"):
        self.risk_mode = risk_mode

    def detect(self, symbol, candles, indicator_context=None, session_context=None):
        return regime_context(risk_mode=self.risk_mode)


def verify_files() -> bool:
    files = [
        "backend/strategy_engine/confluence_score_engine.py",
        "backend/strategy_engine/signal_reason_builder.py",
        "docs/phase-6-day-7-progress.md",
    ]
    missing = [path for path in files if not (PROJECT_ROOT / path).is_file()]
    return show("Confluence scorer, reason builder, and docs files exist", not missing, ", ".join(missing))


def verify_models() -> bool:
    try:
        from backend.strategy_engine.strategy_models import ConfluenceScoreBreakdown, XAUUSDStrategySignal

        expected_breakdown = {
            "session_score",
            "indicator_score",
            "liquidity_score",
            "structure_score",
            "fvg_score",
            "order_block_score",
            "regime_score",
            "total_score",
            "confidence",
            "trade_quality",
            "missing_confirmations",
            "aligned_confirmations",
            "risk_mode",
            "warnings",
        }
        expected_signal = {
            "confluence_score",
            "trade_quality",
            "aligned_confirmations",
            "missing_confirmations",
            "client_summary",
            "technical_summary",
        }
        passed = expected_breakdown <= set(ConfluenceScoreBreakdown.model_fields) and expected_signal <= set(XAUUSDStrategySignal.model_fields)
        return show("ConfluenceScoreBreakdown model and signal fields exist", passed)
    except Exception as exc:
        return show("ConfluenceScoreBreakdown model and signal fields exist", False, str(exc))


def verify_no_confluence_wait() -> bool:
    try:
        from backend.strategy_engine.xauusd_strategy_engine import XAUUSDStrategyEngine

        signal = XAUUSDStrategyEngine().analyze()
        passed = (
            signal.action == "WAIT"
            and signal.execution_allowed is False
            and signal.confluence_score.confidence <= 40
            and signal.trade_quality == "NO_TRADE"
        )
        return show("No-confluence analysis returns WAIT with low confidence", passed)
    except Exception as exc:
        return show("No-confluence analysis returns WAIT with low confidence", False, str(exc))


def verify_strong_bullish_bearish() -> bool:
    try:
        from backend.strategy_engine.xauusd_strategy_engine import XAUUSDStrategyEngine

        bullish = XAUUSDStrategyEngine(
            session_service=FakeSessionService(),
            indicator_builder=FakeIndicatorBuilder(),
            liquidity_detector=FakeLiquidityDetector("SELL_SIDE_SWEEP"),
            smc_detector=FakeSMCDetector("BULLISH"),
            regime_detector=FakeRegimeDetector(),
        ).analyze(candles=[{"time": "2026-01-02T07:00:00+00:00", "open": 1, "high": 2, "low": 0.5, "close": 1.5}])
        bearish = XAUUSDStrategyEngine(
            session_service=FakeSessionService(),
            indicator_builder=FakeIndicatorBuilder(),
            liquidity_detector=FakeLiquidityDetector("BUY_SIDE_SWEEP"),
            smc_detector=FakeSMCDetector("BEARISH"),
            regime_detector=FakeRegimeDetector(),
        ).analyze(candles=[{"time": "2026-01-02T07:00:00+00:00", "open": 2, "high": 2.5, "low": 1, "close": 1.5}])
        passed = (
            bullish.action == "BUY"
            and bullish.confidence >= 70
            and bullish.execution_allowed is False
            and bearish.action == "SELL"
            and bearish.confidence >= 70
            and bearish.execution_allowed is False
        )
        return show("Strong bullish and bearish confluence produce BUY/SELL candidates", passed)
    except Exception as exc:
        return show("Strong bullish and bearish confluence produce BUY/SELL candidates", False, str(exc))


def verify_confidence_caps_and_regime_block() -> bool:
    try:
        from backend.strategy_engine.confluence_score_engine import ConfluenceScoreEngine

        engine = ConfluenceScoreEngine()
        no_liquidity = engine.score(session_context(), indicator_context(), liquidity_context("NONE"), smc_context(), regime_context())
        no_structure = engine.score(session_context(), indicator_context(), liquidity_context(), smc_context(with_structure=False), regime_context())
        no_trade_regime = engine.score(session_context(), indicator_context(), liquidity_context(), smc_context(), regime_context("UNCLEAR", "NO_TRADE"))
        passed = (
            no_liquidity.confidence <= 40
            and no_structure.confidence <= 50
            and no_trade_regime.risk_mode == "NO_TRADE"
            and no_trade_regime.trade_quality == "NO_TRADE"
            and no_trade_regime.confidence <= 20
        )
        return show("Confidence caps and regime NO_TRADE hard block work", passed)
    except Exception as exc:
        return show("Confidence caps and regime NO_TRADE hard block work", False, str(exc))


def verify_summaries() -> bool:
    try:
        from backend.strategy_engine.signal_reason_builder import SignalReasonBuilder
        from backend.strategy_engine.confluence_score_engine import ConfluenceScoreEngine

        score = ConfluenceScoreEngine().score(session_context(), indicator_context(), liquidity_context(), smc_context(), regime_context())
        technical = SignalReasonBuilder().build_technical_summary(
            {"liquidity_context": liquidity_context(), "smc_context": smc_context(), "regime_context": regime_context()},
            score,
        )
        missing = SignalReasonBuilder().build_missing_confirmation_text(score)
        passed = technical and "sweep=" in technical and "regime=" in technical and isinstance(missing, str)
        return show("Client and technical summary builders generate text", passed)
    except Exception as exc:
        return show("Client and technical summary builders generate text", False, str(exc))


def verify_routes_and_signal_payload() -> bool:
    try:
        from backend.main import app

        client = TestClient(app)
        get_response = client.get("/strategy/confluence/xauusd")
        post_response = client.post("/strategy/confluence/xauusd/analyze", json={})
        analyze_response = client.post("/strategy/analyze/xauusd", json={})
        confluence_payload = post_response.json()
        signal_payload = analyze_response.json()
        passed = (
            get_response.status_code == 200
            and post_response.status_code == 200
            and analyze_response.status_code == 200
            and "confluence_breakdown" in confluence_payload
            and "client_summary" in confluence_payload
            and "technical_summary" in confluence_payload
            and "confluence_score" in signal_payload
            and signal_payload["execution_allowed"] is False
        )
        return show("Confluence API route and XAUUSD signal payload work", passed)
    except Exception as exc:
        return show("Confluence API route and XAUUSD signal payload work", False, str(exc))


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
        expected_phase6 = {
            "/strategy/status",
            "/strategy/analyze/xauusd",
            "/strategy/liquidity/xauusd",
            "/strategy/liquidity/xauusd/analyze",
            "/strategy/structure/xauusd",
            "/strategy/structure/xauusd/analyze",
            "/strategy/fvg/xauusd",
            "/strategy/fvg/xauusd/analyze",
            "/strategy/order-block/xauusd",
            "/strategy/order-block/xauusd/analyze",
            "/strategy/regime/xauusd",
            "/strategy/regime/xauusd/analyze",
            "/strategy/confluence/xauusd",
            "/strategy/confluence/xauusd/analyze",
            "/strategy/signals",
            "/strategy/signals/{signal_id}",
            "/strategy/session-context",
        }
        all_route_paths = {route.path for route in app.routes}
        missing = sorted(REQUIRED_GET_ROUTES - registered_get_routes)
        missing += sorted(expected_phase6 - all_route_paths)
        missing_ws = sorted(REQUIRED_WEBSOCKET_ROUTES - registered_websockets)
        return show("Phase 6 Day 1-6 and Phase 5 routes are preserved", not missing and not missing_ws, ", ".join(missing + missing_ws))
    except Exception as exc:
        return show("Phase 6 Day 1-6 and Phase 5 routes are preserved", False, str(exc))


def main() -> int:
    print("Phase 6 Day 7 Final Confluence Verification")
    print("=" * 55)
    checks = [
        verify_files(),
        verify_models(),
        verify_no_confluence_wait(),
        verify_strong_bullish_bearish(),
        verify_confidence_caps_and_regime_block(),
        verify_summaries(),
        verify_routes_and_signal_payload(),
        verify_order_send_isolated(),
        verify_preserved_routes(),
    ]
    print("=" * 55)
    print("PASS" if all(checks) else "FAIL")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
