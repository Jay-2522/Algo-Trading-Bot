from uuid import uuid4

from backend.strategy_engine.indicator_context_builder import IndicatorContextBuilder
from backend.strategy_engine.liquidity_sweep_detector import LiquiditySweepDetector
from backend.strategy_engine.market_session_service import MarketSessionService
from backend.strategy_engine.smc_structure_detector import SMCStructureDetector
from backend.strategy_engine.strategy_models import XAUUSDStrategySignal


class XAUUSDStrategyEngine:
    """Analysis-only XAUUSD strategy engine foundation."""

    def __init__(
        self,
        session_service: MarketSessionService | None = None,
        indicator_builder: IndicatorContextBuilder | None = None,
        liquidity_detector: LiquiditySweepDetector | None = None,
        smc_detector: SMCStructureDetector | None = None,
    ) -> None:
        self.session_service = session_service or MarketSessionService()
        self.indicator_builder = indicator_builder or IndicatorContextBuilder()
        self.liquidity_detector = liquidity_detector or LiquiditySweepDetector()
        self.smc_detector = smc_detector or SMCStructureDetector()

    def analyze(self, symbol: str = "XAUUSD", candles: list | None = None) -> XAUUSDStrategySignal:
        normalized_symbol = symbol.upper()
        session_context = self.session_service.get_session_context()
        indicator_context = self.indicator_builder.build_context(normalized_symbol, "H1", candles)
        liquidity_context = self.liquidity_detector.detect(normalized_symbol, candles)
        smc_context = self.smc_detector.detect(
            normalized_symbol,
            candles,
            liquidity_context=liquidity_context,
            session_context=session_context,
        )

        confidence = self._confidence(session_context, indicator_context, liquidity_context, smc_context)
        action = "WAIT"
        reason = (
            "Waiting for complete XAUUSD confluence. "
            f"Liquidity sweep={liquidity_context.sweep_direction}, "
            f"level={liquidity_context.active_sweep_level or 'NONE'}, "
            f"quality={liquidity_context.sweep_quality}, "
            f"confidence={liquidity_context.confidence}. "
            f"Structure bos={smc_context.bos_direction}, "
            f"choch={smc_context.choch_direction}, "
            f"post_sweep_confirmation={smc_context.post_sweep_confirmation}. "
            f"FVG direction={smc_context.fvg_direction}, "
            f"quality={smc_context.fvg_quality}, "
            f"aligned={smc_context.latest_fvg.aligned_with_structure if smc_context.latest_fvg else False}. "
            "Waiting because liquidity, market structure, and active FVG confirmation are not fully aligned."
        )

        if self._buy_conditions(session_context, indicator_context, liquidity_context, smc_context):
            action = "BUY"
            reason = (
                "BUY candidate only: sell-side liquidity sweep has bullish BOS/CHOCH confirmation "
                "and a bullish active FVG during a high-quality session. Execution remains disabled."
            )
        elif self._sell_conditions(session_context, indicator_context, liquidity_context, smc_context):
            action = "SELL"
            reason = (
                "SELL candidate only: buy-side liquidity sweep has bearish BOS/CHOCH confirmation "
                "and a bearish active FVG during a high-quality session. Execution remains disabled."
            )

        return XAUUSDStrategySignal(
            signal_id=f"xauusd-{uuid4().hex}",
            symbol=normalized_symbol,
            action=action,
            confidence=confidence,
            trend_bias=indicator_context.trend_bias,
            session_context=session_context,
            indicator_context=indicator_context,
            liquidity_context=liquidity_context,
            smc_context=smc_context,
            risk_notes=[
                "Phase 6 Day 1 is strategy analysis only.",
                "Execution is disabled; signal output cannot place trades.",
            ],
            execution_allowed=False,
            reason=reason,
            metadata={
                "strategy": "XAUUSD",
                "timeframes": ["H1", "H4"],
                "mode": "analysis_only",
                "simulation_only": True,
                "live_execution_enabled": False,
                "broker_execution_enabled": False,
            },
        )

    def _confidence(self, session_context, indicator_context, liquidity_context, smc_context) -> float:
        score = 0.0
        if session_context.session_quality == "HIGH":
            score += 20.0
        elif session_context.session_quality == "MEDIUM":
            score += 10.0

        if indicator_context.trend_bias != "NEUTRAL":
            score += 25.0
        if indicator_context.rsi is not None:
            score += 10.0
        if liquidity_context.sweep_direction != "NONE":
            score += (liquidity_context.confidence / 100.0) * 25.0
        if smc_context.structure_bias != "NEUTRAL":
            score += (smc_context.confidence / 100.0) * 20.0
        if smc_context.active_fvg_detected:
            score += (smc_context.fvg_confidence / 100.0) * 10.0

        return round(min(score, 100.0), 2)

    def _buy_conditions(self, session_context, indicator_context, liquidity_context, smc_context) -> bool:
        return (
            liquidity_context.sweep_direction == "SELL_SIDE_SWEEP"
            and (smc_context.bos_direction == "BULLISH_BOS" or smc_context.choch_direction == "BULLISH_CHOCH")
            and smc_context.post_sweep_confirmation is True
            and smc_context.active_fvg_detected is True
            and smc_context.fvg_direction == "BULLISH"
            and session_context.session_quality == "HIGH"
        )

    def _sell_conditions(self, session_context, indicator_context, liquidity_context, smc_context) -> bool:
        return (
            liquidity_context.sweep_direction == "BUY_SIDE_SWEEP"
            and (smc_context.bos_direction == "BEARISH_BOS" or smc_context.choch_direction == "BEARISH_CHOCH")
            and smc_context.post_sweep_confirmation is True
            and smc_context.active_fvg_detected is True
            and smc_context.fvg_direction == "BEARISH"
            and session_context.session_quality == "HIGH"
        )
