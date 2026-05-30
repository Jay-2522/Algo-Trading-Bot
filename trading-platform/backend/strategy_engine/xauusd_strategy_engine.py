from uuid import uuid4

from backend.strategy_engine.confluence_score_engine import ConfluenceScoreEngine
from backend.strategy_engine.indicator_context_builder import IndicatorContextBuilder
from backend.strategy_engine.liquidity_sweep_detector import LiquiditySweepDetector
from backend.strategy_engine.market_regime_detector import MarketRegimeDetector
from backend.strategy_engine.market_session_service import MarketSessionService
from backend.strategy_engine.signal_reason_builder import SignalReasonBuilder
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
        confluence_engine: ConfluenceScoreEngine | None = None,
        reason_builder: SignalReasonBuilder | None = None,
    ) -> None:
        self.session_service = session_service or MarketSessionService()
        self.indicator_builder = indicator_builder or IndicatorContextBuilder()
        self.liquidity_detector = liquidity_detector or LiquiditySweepDetector()
        self.smc_detector = smc_detector or SMCStructureDetector()
        self.regime_detector = regime_detector or MarketRegimeDetector()
        self.confluence_engine = confluence_engine or ConfluenceScoreEngine()
        self.reason_builder = reason_builder or SignalReasonBuilder()

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

        confluence_score = self.confluence_engine.score(
            session_context=session_context,
            indicator_context=indicator_context,
            liquidity_context=liquidity_context,
            smc_context=smc_context,
            regime_context=regime_context,
        )
        confidence = confluence_score.confidence
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

        if confluence_score.risk_mode == "NO_TRADE":
            reason = f"WAIT: confluence risk mode is NO_TRADE. {reason}"
        elif regime_context.regime == "HIGH_VOLATILITY":
            reason = f"WAIT: high-volatility regime detected; volatility protection blocks candidate signals. {reason}"
        elif regime_context.regime == "LOW_VOLATILITY":
            reason = f"WAIT: low-volatility regime detected; movement quality is too poor for XAUUSD confluence. {reason}"
        elif regime_context.regime == "UNCLEAR":
            reason = f"WAIT: market regime is unclear, so strategy confidence is not actionable. {reason}"
        elif self._buy_conditions(liquidity_context, smc_context, regime_context, confluence_score):
            action = "BUY"
            reason = (
                "BUY candidate only: sell-side liquidity sweep has bullish BOS/CHOCH confirmation "
                "with bullish active FVG/order block, acceptable market regime, and sufficient confluence confidence. Execution remains disabled."
            )
        elif self._sell_conditions(liquidity_context, smc_context, regime_context, confluence_score):
            action = "SELL"
            reason = (
                "SELL candidate only: buy-side liquidity sweep has bearish BOS/CHOCH confirmation "
                "with bearish active FVG/order block, acceptable market regime, and sufficient confluence confidence. Execution remains disabled."
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
        risk_notes.extend(confluence_score.warnings)

        technical_summary = self.reason_builder.build_technical_summary(
            {
                "session_context": session_context,
                "indicator_context": indicator_context,
                "liquidity_context": liquidity_context,
                "smc_context": smc_context,
                "regime_context": regime_context,
            },
            confluence_score,
        )
        signal = XAUUSDStrategySignal(
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
            confluence_score=confluence_score,
            trade_quality=confluence_score.trade_quality,
            aligned_confirmations=confluence_score.aligned_confirmations,
            missing_confirmations=confluence_score.missing_confirmations,
            client_summary="",
            technical_summary=technical_summary,
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
        signal.client_summary = self.reason_builder.build_client_summary(signal)
        return signal

    def _buy_conditions(self, liquidity_context, smc_context, regime_context, confluence_score) -> bool:
        return (
            liquidity_context.sweep_direction == "SELL_SIDE_SWEEP"
            and (smc_context.bos_direction == "BULLISH_BOS" or smc_context.choch_direction == "BULLISH_CHOCH")
            and (
                (smc_context.active_fvg_detected is True and smc_context.fvg_direction == "BULLISH")
                or (
                    smc_context.active_order_block_detected is True
                    and smc_context.order_block_direction == "BULLISH"
                )
            )
            and regime_context.tradeability != "AVOID"
            and regime_context.risk_mode != "NO_TRADE"
            and confluence_score.confidence >= 70.0
        )

    def _sell_conditions(self, liquidity_context, smc_context, regime_context, confluence_score) -> bool:
        return (
            liquidity_context.sweep_direction == "BUY_SIDE_SWEEP"
            and (smc_context.bos_direction == "BEARISH_BOS" or smc_context.choch_direction == "BEARISH_CHOCH")
            and (
                (smc_context.active_fvg_detected is True and smc_context.fvg_direction == "BEARISH")
                or (
                    smc_context.active_order_block_detected is True
                    and smc_context.order_block_direction == "BEARISH"
                )
            )
            and regime_context.tradeability != "AVOID"
            and regime_context.risk_mode != "NO_TRADE"
            and confluence_score.confidence >= 70.0
        )
