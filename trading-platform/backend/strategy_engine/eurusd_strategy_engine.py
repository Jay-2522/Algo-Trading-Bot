from uuid import uuid4

from backend.strategy_engine.indicator_context_builder import IndicatorContextBuilder
from backend.strategy_engine.market_session_service import MarketSessionService
from backend.strategy_engine.strategy_models import EURUSDStrategySignal, IndicatorContext, MarketSessionContext


class EURUSDStrategyEngine:
    """Phase 8 Day 1 analysis-only EURUSD strategy foundation."""

    def __init__(
        self,
        session_service: MarketSessionService | None = None,
        indicator_builder: IndicatorContextBuilder | None = None,
    ) -> None:
        self.session_service = session_service or MarketSessionService()
        self.indicator_builder = indicator_builder or IndicatorContextBuilder()

    def analyze(self, candles: list | None = None) -> EURUSDStrategySignal:
        session_context = self.build_session_context()
        indicator_context = self.build_indicator_context(candles=candles)
        return self.generate_signal(session_context=session_context, indicator_context=indicator_context)

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

    def generate_signal(
        self,
        session_context: MarketSessionContext,
        indicator_context: IndicatorContext,
    ) -> EURUSDStrategySignal:
        return EURUSDStrategySignal(
            signal_id=f"eurusd-{uuid4().hex}",
            symbol="EURUSD",
            action="WAIT",
            confidence=10.0,
            trend_bias=indicator_context.trend_bias,
            session_context=session_context,
            indicator_context=indicator_context,
            execution_allowed=False,
            reason="Phase 8 Day 1 foundation established. EURUSD confluence layers are not yet integrated.",
            metadata={
                "instrument": "EURUSD",
                "phase": "PHASE_8_DAY_1",
                "mode": "analysis_only",
                "session_ready": True,
                "indicator_context_ready": True,
                "liquidity_engine_integrated": False,
                "smc_engine_integrated": False,
                "news_intelligence_ready": True,
                "simulation_only": True,
                "live_execution_enabled": False,
                "broker_execution_enabled": False,
            },
        )
