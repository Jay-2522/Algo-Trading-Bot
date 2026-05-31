from uuid import uuid4

from backend.strategy_engine.eurusd_fvg_engine import EURUSDFVGEngine
from backend.strategy_engine.eurusd_liquidity_engine import EURUSDLiquidityEngine
from backend.strategy_engine.eurusd_order_block_engine import EURUSDOrderBlockEngine
from backend.strategy_engine.eurusd_regime_engine import EURUSDRegimeEngine
from backend.strategy_engine.eurusd_structure_engine import EURUSDStructureEngine
from backend.strategy_engine.indicator_context_builder import IndicatorContextBuilder
from backend.strategy_engine.market_session_service import MarketSessionService
from backend.strategy_engine.strategy_models import (
    EURUSDFVGContext,
    EURUSDLiquidityContext,
    EURUSDOrderBlockContext,
    EURUSDRegimeContext,
    EURUSDStrategySignal,
    EURUSDStructureContext,
    IndicatorContext,
    MarketSessionContext,
)


class EURUSDStrategyEngine:
    """Phase 8 Day 1 analysis-only EURUSD strategy foundation."""

    def __init__(
        self,
        session_service: MarketSessionService | None = None,
        indicator_builder: IndicatorContextBuilder | None = None,
        liquidity_engine: EURUSDLiquidityEngine | None = None,
        structure_engine: EURUSDStructureEngine | None = None,
        fvg_engine: EURUSDFVGEngine | None = None,
        order_block_engine: EURUSDOrderBlockEngine | None = None,
        regime_engine: EURUSDRegimeEngine | None = None,
    ) -> None:
        self.session_service = session_service or MarketSessionService()
        self.indicator_builder = indicator_builder or IndicatorContextBuilder()
        self.liquidity_engine = liquidity_engine or EURUSDLiquidityEngine(session_service=self.session_service)
        self.structure_engine = structure_engine or EURUSDStructureEngine(session_service=self.session_service)
        self.fvg_engine = fvg_engine or EURUSDFVGEngine(session_service=self.session_service)
        self.order_block_engine = order_block_engine or EURUSDOrderBlockEngine(session_service=self.session_service)
        self.regime_engine = regime_engine or EURUSDRegimeEngine()

    def analyze(self, candles: list | None = None) -> EURUSDStrategySignal:
        session_context = self.build_session_context()
        indicator_context = self.build_indicator_context(candles=candles)
        liquidity_context = self.build_liquidity_context(candles=candles)
        structure_context = self.build_structure_context(candles=candles, liquidity_context=liquidity_context)
        fvg_context = self.build_fvg_context(
            candles=candles,
            structure_context=structure_context,
            liquidity_context=liquidity_context,
        )
        order_block_context = self.build_order_block_context(
            candles=candles,
            structure_context=structure_context,
            liquidity_context=liquidity_context,
            fvg_context=fvg_context,
        )
        regime_context = self.build_regime_context(
            candles=candles,
            indicator_context=indicator_context,
            session_context=session_context,
        )
        return self.generate_signal(
            session_context=session_context,
            indicator_context=indicator_context,
            liquidity_context=liquidity_context,
            structure_context=structure_context,
            fvg_context=fvg_context,
            order_block_context=order_block_context,
            regime_context=regime_context,
        )

    def build_session_context(self) -> MarketSessionContext:
        context = self.session_service.get_session_context()
        warnings = list(context.warnings)
        if context.current_session == "ASIAN":
            warnings.append("EURUSD Asian session is monitored but London/New York sessions are preferred.")
        return context.model_copy(update={"warnings": warnings})

    def build_indicator_context(self, candles: list | None = None) -> IndicatorContext:
        context = self.indicator_builder.build_context(symbol="EURUSD", timeframe="H1", candles=candles)
        warnings = list(context.warnings)
        if not candles:
            warnings.append("Phase 8 Day 1 EURUSD indicator context uses safe placeholders until data wiring is expanded.")
        return context.model_copy(update={"symbol": "EURUSD", "warnings": warnings})

    def build_liquidity_context(self, candles: list | None = None) -> EURUSDLiquidityContext:
        return self.liquidity_engine.detect(candles=candles)

    def build_structure_context(
        self,
        candles: list | None = None,
        liquidity_context: EURUSDLiquidityContext | None = None,
    ) -> EURUSDStructureContext:
        return self.structure_engine.detect(
            candles=candles,
            liquidity_context=liquidity_context or self.build_liquidity_context(candles=candles),
        )

    def build_fvg_context(
        self,
        candles: list | None = None,
        structure_context: EURUSDStructureContext | None = None,
        liquidity_context: EURUSDLiquidityContext | None = None,
    ) -> EURUSDFVGContext:
        resolved_liquidity = liquidity_context or self.build_liquidity_context(candles=candles)
        resolved_structure = structure_context or self.build_structure_context(
            candles=candles,
            liquidity_context=resolved_liquidity,
        )
        return self.fvg_engine.detect(
            candles=candles,
            structure_context=resolved_structure,
            liquidity_context=resolved_liquidity,
        )

    def build_order_block_context(
        self,
        candles: list | None = None,
        structure_context: EURUSDStructureContext | None = None,
        liquidity_context: EURUSDLiquidityContext | None = None,
        fvg_context: EURUSDFVGContext | None = None,
    ) -> EURUSDOrderBlockContext:
        resolved_liquidity = liquidity_context or self.build_liquidity_context(candles=candles)
        resolved_structure = structure_context or self.build_structure_context(
            candles=candles,
            liquidity_context=resolved_liquidity,
        )
        resolved_fvg = fvg_context or self.build_fvg_context(
            candles=candles,
            structure_context=resolved_structure,
            liquidity_context=resolved_liquidity,
        )
        return self.order_block_engine.detect(
            candles=candles,
            structure_context=resolved_structure,
            liquidity_context=resolved_liquidity,
            fvg_context=resolved_fvg,
        )

    def build_regime_context(
        self,
        candles: list | None = None,
        indicator_context: IndicatorContext | None = None,
        session_context: MarketSessionContext | None = None,
    ) -> EURUSDRegimeContext:
        return self.regime_engine.detect(
            candles=candles,
            indicator_context=indicator_context or self.build_indicator_context(candles=candles),
            session_context=session_context or self.build_session_context(),
        )

    def generate_signal(
        self,
        session_context: MarketSessionContext,
        indicator_context: IndicatorContext,
        liquidity_context: EURUSDLiquidityContext,
        structure_context: EURUSDStructureContext,
        fvg_context: EURUSDFVGContext,
        order_block_context: EURUSDOrderBlockContext,
        regime_context: EURUSDRegimeContext,
    ) -> EURUSDStrategySignal:
        confidence = 10.0
        regime_note = ""
        if regime_context.regime == "HIGH_VOLATILITY":
            confidence = 5.0
            regime_note = " High-volatility protection is active."
        elif regime_context.regime == "LOW_VOLATILITY":
            confidence = 5.0
            regime_note = " Weak EURUSD movement keeps the signal in WAIT."
        elif regime_context.regime == "RANGING":
            confidence = 8.0
            regime_note = " Ranging conditions reduce confidence."
        elif regime_context.regime == "TRENDING":
            confidence = 15.0
            regime_note = " Trending conditions can support future confluence scoring."
        elif regime_context.regime == "UNCLEAR":
            confidence = 5.0
            regime_note = " Unclear regime keeps the strategy defensive."
        return EURUSDStrategySignal(
            signal_id=f"eurusd-{uuid4().hex}",
            symbol="EURUSD",
            action="WAIT",
            confidence=confidence,
            trend_bias=indicator_context.trend_bias,
            session_context=session_context,
            indicator_context=indicator_context,
            liquidity_context=liquidity_context,
            structure_context=structure_context,
            fvg_context=fvg_context,
            order_block_context=order_block_context,
            regime_context=regime_context,
            execution_allowed=False,
            reason=(
                "Phase 8 Day 6 EURUSD market regime layer established. "
                f"Sweep direction={liquidity_context.sweep_direction}, "
                f"active level={liquidity_context.active_sweep_level or 'NONE'}, "
                f"quality={liquidity_context.sweep_quality}, "
                f"liquidity confidence={liquidity_context.confidence}. "
                f"BOS={structure_context.bos_direction}, "
                f"CHOCH={structure_context.choch_direction}, "
                f"post_sweep_confirmation={structure_context.post_sweep_confirmation}, "
                f"structure_quality={structure_context.structure_quality}. "
                f"FVG direction={fvg_context.fvg_direction}, "
                f"active_fvg={fvg_context.active_fvg_detected}, "
                f"fvg_quality={fvg_context.fvg_quality}. "
                f"Order block direction={order_block_context.order_block_direction}, "
                f"active_ob={order_block_context.active_order_block_detected}, "
                f"ob_quality={order_block_context.order_block_quality}, "
                f"ob_confidence={order_block_context.order_block_confidence}. "
                f"Regime={regime_context.regime}, "
                f"tradeability={regime_context.tradeability}, "
                f"risk_mode={regime_context.risk_mode}, "
                f"regime_confidence={regime_context.confidence}."
                f"{regime_note} "
                "EURUSD confluence layer is not yet integrated."
            ),
            metadata={
                "instrument": "EURUSD",
                "phase": "PHASE_8_DAY_6",
                "mode": "analysis_only",
                "session_ready": True,
                "indicator_context_ready": True,
                "liquidity_engine_integrated": True,
                "eurusd_liquidity_tolerance": self.liquidity_engine.tolerance,
                "structure_engine_integrated": True,
                "eurusd_structure_tolerance": self.structure_engine.tolerance,
                "fvg_engine_integrated": True,
                "eurusd_fvg_tolerance": self.fvg_engine.tolerance,
                "eurusd_fvg_min_gap_size": self.fvg_engine.min_gap_size,
                "order_block_engine_integrated": True,
                "eurusd_order_block_tolerance": self.order_block_engine.tolerance,
                "eurusd_order_block_min_candle_range": self.order_block_engine.min_candle_range,
                "regime_engine_integrated": True,
                "smc_engine_integrated": True,
                "news_intelligence_ready": True,
                "simulation_only": True,
                "live_execution_enabled": False,
                "broker_execution_enabled": False,
            },
        )
