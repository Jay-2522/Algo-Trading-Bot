from uuid import uuid4

from backend.strategy_engine.indicator_context_builder import IndicatorContextBuilder
from backend.strategy_engine.liquidity_sweep_detector import LiquiditySweepDetector
from backend.strategy_engine.market_regime_detector import MarketRegimeDetector
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
        regime_detector: MarketRegimeDetector | None = None,
    ) -> None:
        self.session_service = session_service or MarketSessionService()
        self.indicator_builder = indicator_builder or IndicatorContextBuilder()
        self.liquidity_detector = liquidity_detector or LiquiditySweepDetector()
        self.smc_detector = smc_detector or SMCStructureDetector()
        self.regime_detector = regime_detector or MarketRegimeDetector()

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
        regime_context = self.regime_detector.detect(
            symbol=normalized_symbol,
            candles=candles,
            indicator_context=indicator_context,
            session_context=session_context,
        )

        confidence = self._confidence(session_context, indicator_context, liquidity_context, smc_context, regime_context)
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
            f"Order block direction={smc_context.order_block_direction}, "
            f"quality={smc_context.order_block_quality}, "
            f"active={smc_context.active_order_block_detected}. "
            f"Regime={regime_context.regime}, "
            f"tradeability={regime_context.tradeability}, "
            f"risk_mode={regime_context.risk_mode}. "
            "Waiting because liquidity, market structure, active FVG, active order block, and regime confirmation are not fully aligned."
        )

        if regime_context.regime == "HIGH_VOLATILITY":
            reason = f"WAIT: high-volatility regime detected; volatility protection blocks candidate signals. {reason}"
        elif regime_context.regime == "LOW_VOLATILITY":
            reason = f"WAIT: low-volatility regime detected; movement quality is too poor for XAUUSD confluence. {reason}"
        elif regime_context.regime == "UNCLEAR":
            reason = f"WAIT: market regime is unclear, so strategy confidence is not actionable. {reason}"
        elif self._buy_conditions(session_context, indicator_context, liquidity_context, smc_context, regime_context):
            action = "BUY"
            reason = (
                "BUY candidate only: sell-side liquidity sweep has bullish BOS/CHOCH confirmation "
                "with bullish active FVG, bullish active order block, and acceptable market regime. Execution remains disabled."
            )
        elif self._sell_conditions(session_context, indicator_context, liquidity_context, smc_context, regime_context):
            action = "SELL"
            reason = (
                "SELL candidate only: buy-side liquidity sweep has bearish BOS/CHOCH confirmation "
                "with bearish active FVG, bearish active order block, and acceptable market regime. Execution remains disabled."
            )

        risk_notes = [
            "Phase 6 strategy analysis only.",
            "Execution is disabled; signal output cannot place trades.",
        ]
        if regime_context.regime == "HIGH_VOLATILITY":
            risk_notes.append("Volatility protection active: high-volatility regime should usually remain WAIT.")
        if regime_context.regime == "LOW_VOLATILITY":
            risk_notes.append("Low-volatility protection active: poor movement quality should usually remain WAIT.")
        if regime_context.regime == "RANGING":
            risk_notes.append("Ranging regime: stronger confluence is required and confidence is reduced.")

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
            regime_context=regime_context,
            risk_notes=risk_notes,
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

    def _confidence(self, session_context, indicator_context, liquidity_context, smc_context, regime_context) -> float:
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
        if smc_context.active_order_block_detected:
            score += (smc_context.order_block_confidence / 100.0) * 10.0
        if regime_context.regime == "TRENDING":
            score += (regime_context.confidence / 100.0) * 15.0
        elif regime_context.regime == "RANGING":
            score -= 10.0
        elif regime_context.regime in {"HIGH_VOLATILITY", "LOW_VOLATILITY", "UNCLEAR"}:
            score -= 20.0

        return round(max(0.0, min(score, 100.0)), 2)

    def _buy_conditions(self, session_context, indicator_context, liquidity_context, smc_context, regime_context) -> bool:
        return (
            self._regime_allows_candidate(regime_context, smc_context)
            and
            liquidity_context.sweep_direction == "SELL_SIDE_SWEEP"
            and (smc_context.bos_direction == "BULLISH_BOS" or smc_context.choch_direction == "BULLISH_CHOCH")
            and smc_context.post_sweep_confirmation is True
            and smc_context.active_fvg_detected is True
            and smc_context.fvg_direction == "BULLISH"
            and smc_context.active_order_block_detected is True
            and smc_context.order_block_direction == "BULLISH"
            and session_context.session_quality == "HIGH"
        )

    def _sell_conditions(self, session_context, indicator_context, liquidity_context, smc_context, regime_context) -> bool:
        return (
            self._regime_allows_candidate(regime_context, smc_context)
            and
            liquidity_context.sweep_direction == "BUY_SIDE_SWEEP"
            and (smc_context.bos_direction == "BEARISH_BOS" or smc_context.choch_direction == "BEARISH_CHOCH")
            and smc_context.post_sweep_confirmation is True
            and smc_context.active_fvg_detected is True
            and smc_context.fvg_direction == "BEARISH"
            and smc_context.active_order_block_detected is True
            and smc_context.order_block_direction == "BEARISH"
            and session_context.session_quality == "HIGH"
        )

    def _regime_allows_candidate(self, regime_context, smc_context) -> bool:
        if regime_context.regime == "TRENDING":
            return regime_context.tradeability in {"HIGH", "MEDIUM"} and regime_context.risk_mode == "NORMAL"
        if regime_context.regime == "RANGING":
            return (
                regime_context.tradeability == "MEDIUM"
                and smc_context.fvg_quality == "HIGH"
                and smc_context.order_block_quality == "HIGH"
            )
        return False
