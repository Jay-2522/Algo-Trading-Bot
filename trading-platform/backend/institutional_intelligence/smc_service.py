from typing import Any

from backend.institutional_intelligence.institutional_context import InstitutionalContextBuilder
from backend.institutional_intelligence.smc_models import InstitutionalContext
from backend.institutional_intelligence.liquidity_sweep_models import SweepContext
from backend.institutional_intelligence.sweep_context_builder import SweepContextBuilder
from backend.institutional_intelligence.fair_value_gap_models import FVGContext
from backend.institutional_intelligence.fvg_context_builder import FVGContextBuilder
from backend.institutional_intelligence.order_block_models import OrderBlockContext
from backend.institutional_intelligence.order_block_context_builder import OrderBlockContextBuilder
from backend.institutional_intelligence.breaker_block_models import BreakerBlockContext
from backend.institutional_intelligence.breaker_block_context_builder import BreakerBlockContextBuilder
from backend.institutional_intelligence.structure_shift_models import StructureShiftContext
from backend.institutional_intelligence.structure_shift_context_builder import StructureShiftContextBuilder
from backend.institutional_intelligence.confluence_models import ConfluenceContext
from backend.institutional_intelligence.confluence_context_builder import ConfluenceContextBuilder
from backend.institutional_intelligence.multi_timeframe_models import MultiTimeframeAlignment
from backend.institutional_intelligence.multi_timeframe_alignment_engine import MultiTimeframeAlignmentEngine
from backend.institutional_intelligence.session_models import SessionIntelligenceContext
from backend.institutional_intelligence.session_context_builder import SessionContextBuilder
from backend.institutional_intelligence.entry_model_models import EntryModelContext
from backend.institutional_intelligence.entry_model_context_builder import EntryModelContextBuilder
from backend.institutional_intelligence.setup_validator_models import SetupValidationContext
from backend.institutional_intelligence.setup_validation_context_builder import SetupValidationContextBuilder
from backend.institutional_intelligence.simulation_decision_models import SimulationDecisionContext
from backend.institutional_intelligence.simulation_decision_context_builder import SimulationDecisionContextBuilder
from backend.institutional_intelligence.paper_trade_models import PaperTradeLifecycleContext
from backend.institutional_intelligence.paper_trade_context_builder import PaperTradeContextBuilder
from backend.institutional_intelligence.position_management_models import (
    EmergencyExitSignal,
    InstitutionalPositionManagement,
    ManagedPosition,
    StructuralExitSignal,
)
from backend.institutional_intelligence.position_management_context_builder import PositionManagementContextBuilder
from backend.institutional_intelligence.institutional_orchestration_models import InstitutionalOrchestrationReport
from backend.institutional_intelligence.institutional_orchestrator import InstitutionalOrchestrator
from backend.institutional_intelligence.ai_reasoning_models import InstitutionalReasoningReport
from backend.institutional_intelligence.institutional_reasoning_engine import InstitutionalReasoningEngine
from backend.institutional_intelligence.reasoning_quality_checker import ReasoningQualityChecker
from backend.institutional_intelligence.performance_analytics_models import InstitutionalPerformanceAnalyticsContext
from backend.institutional_intelligence.performance_analytics_context_builder import PerformanceAnalyticsContextBuilder
from backend.market_data.market_data_service import MarketDataService
from backend.market_data.validators import validate_symbol_name, validate_timeframe
from backend.news_engine.news_filter_service import NewsFilterService
from backend.risk_engine.risk_service import RiskService, get_risk_service
from backend.utils.logger import get_logger


logger = get_logger(__name__)


class SMCService:
    """Analysis service for market structure intelligence; never performs execution."""

    def __init__(
        self,
        market_data_service: MarketDataService | None = None,
        context_builder: InstitutionalContextBuilder | None = None,
        sweep_context_builder: SweepContextBuilder | None = None,
        fvg_context_builder: FVGContextBuilder | None = None,
        order_block_context_builder: OrderBlockContextBuilder | None = None,
        breaker_block_context_builder: BreakerBlockContextBuilder | None = None,
        structure_shift_context_builder: StructureShiftContextBuilder | None = None,
        confluence_context_builder: ConfluenceContextBuilder | None = None,
        multi_timeframe_alignment_engine: MultiTimeframeAlignmentEngine | None = None,
        session_context_builder: SessionContextBuilder | None = None,
        news_filter_service: NewsFilterService | None = None,
        entry_model_context_builder: EntryModelContextBuilder | None = None,
        setup_validation_context_builder: SetupValidationContextBuilder | None = None,
        risk_service: RiskService | None = None,
        simulation_decision_context_builder: SimulationDecisionContextBuilder | None = None,
        paper_trade_context_builder: PaperTradeContextBuilder | None = None,
        position_management_context_builder: PositionManagementContextBuilder | None = None,
        institutional_orchestrator: InstitutionalOrchestrator | None = None,
        institutional_reasoning_engine: InstitutionalReasoningEngine | None = None,
        reasoning_quality_checker: ReasoningQualityChecker | None = None,
        performance_analytics_context_builder: PerformanceAnalyticsContextBuilder | None = None,
    ) -> None:
        self.market_data_service = market_data_service or MarketDataService()
        self.context_builder = context_builder or InstitutionalContextBuilder()
        self.sweep_context_builder = sweep_context_builder or SweepContextBuilder()
        self.fvg_context_builder = fvg_context_builder or FVGContextBuilder()
        self.order_block_context_builder = order_block_context_builder or OrderBlockContextBuilder()
        self.breaker_block_context_builder = breaker_block_context_builder or BreakerBlockContextBuilder()
        self.structure_shift_context_builder = structure_shift_context_builder or StructureShiftContextBuilder()
        self.confluence_context_builder = confluence_context_builder or ConfluenceContextBuilder()
        self.multi_timeframe_alignment_engine = multi_timeframe_alignment_engine or MultiTimeframeAlignmentEngine(
            self.analyze_confluence
        )
        self.session_context_builder = session_context_builder or SessionContextBuilder()
        self.news_filter_service = news_filter_service or NewsFilterService()
        self.entry_model_context_builder = entry_model_context_builder or EntryModelContextBuilder(
            self.confluence_context_builder,
            self.session_context_builder,
        )
        self.setup_validation_context_builder = setup_validation_context_builder or SetupValidationContextBuilder(
            self.entry_model_context_builder
        )
        self.risk_service = risk_service or get_risk_service()
        self.simulation_decision_context_builder = simulation_decision_context_builder or SimulationDecisionContextBuilder(
            self.setup_validation_context_builder
        )
        self.paper_trade_context_builder = paper_trade_context_builder or PaperTradeContextBuilder(
            self.simulation_decision_context_builder
        )
        self.position_management_context_builder = position_management_context_builder or PositionManagementContextBuilder(
            self.paper_trade_context_builder
        )
        self.institutional_orchestrator = institutional_orchestrator or InstitutionalOrchestrator(self)
        self.institutional_reasoning_engine = institutional_reasoning_engine or InstitutionalReasoningEngine()
        self.reasoning_quality_checker = reasoning_quality_checker or ReasoningQualityChecker()
        self.performance_analytics_context_builder = performance_analytics_context_builder or PerformanceAnalyticsContextBuilder()

    def analyze_symbol(self, symbol: str, timeframe: str = "M15") -> InstitutionalContext:
        normalized_symbol = validate_symbol_name(symbol)
        normalized_timeframe = validate_timeframe(timeframe)
        try:
            candles = self.market_data_service.get_candles(normalized_symbol, normalized_timeframe, count=250)
            return self.analyze_from_candles(normalized_symbol, normalized_timeframe, candles)
        except Exception as exc:
            logger.warning("Institutional candle analysis unavailable for %s: %s", normalized_symbol, exc)
            return self.context_builder.build_context(normalized_symbol, normalized_timeframe, [])
        finally:
            self.market_data_service.close()

    def analyze_from_candles(
        self,
        symbol: str,
        timeframe: str,
        candles: list[Any] | None,
    ) -> InstitutionalContext:
        normalized_symbol = validate_symbol_name(symbol)
        normalized_timeframe = validate_timeframe(timeframe)
        return self.context_builder.build_context(normalized_symbol, normalized_timeframe, candles)

    def analyze_liquidity_sweeps(self, symbol: str, timeframe: str = "M15") -> SweepContext:
        normalized_symbol = validate_symbol_name(symbol)
        normalized_timeframe = validate_timeframe(timeframe)
        try:
            candles = self.market_data_service.get_candles(normalized_symbol, normalized_timeframe, count=250)
            return self.analyze_sweeps_from_candles(normalized_symbol, normalized_timeframe, candles)
        except Exception as exc:
            logger.warning("Liquidity sweep analysis unavailable for %s: %s", normalized_symbol, exc)
            return self.sweep_context_builder.build_sweep_context(normalized_symbol, normalized_timeframe, [], [])
        finally:
            self.market_data_service.close()

    def analyze_sweeps_from_candles(
        self,
        symbol: str,
        timeframe: str,
        candles: list[Any] | None,
    ) -> SweepContext:
        normalized_symbol = validate_symbol_name(symbol)
        normalized_timeframe = validate_timeframe(timeframe)
        context = self.context_builder.build_context(normalized_symbol, normalized_timeframe, candles)
        return self.sweep_context_builder.build_sweep_context(
            normalized_symbol,
            normalized_timeframe,
            candles,
            context.liquidity_pools,
        )

    def analyze_fvgs(self, symbol: str, timeframe: str = "M15") -> FVGContext:
        normalized_symbol = validate_symbol_name(symbol)
        normalized_timeframe = validate_timeframe(timeframe)
        try:
            candles = self.market_data_service.get_candles(normalized_symbol, normalized_timeframe, count=250)
            return self.analyze_fvgs_from_candles(normalized_symbol, normalized_timeframe, candles)
        except Exception as exc:
            logger.warning("Fair value gap analysis unavailable for %s: %s", normalized_symbol, exc)
            return self.fvg_context_builder.build_fvg_context(normalized_symbol, normalized_timeframe, [])
        finally:
            self.market_data_service.close()

    def analyze_fvgs_from_candles(
        self,
        symbol: str,
        timeframe: str,
        candles: list[Any] | None,
    ) -> FVGContext:
        normalized_symbol = validate_symbol_name(symbol)
        normalized_timeframe = validate_timeframe(timeframe)
        return self.fvg_context_builder.build_fvg_context(normalized_symbol, normalized_timeframe, candles)

    def analyze_order_blocks(self, symbol: str, timeframe: str = "M15") -> OrderBlockContext:
        normalized_symbol = validate_symbol_name(symbol)
        normalized_timeframe = validate_timeframe(timeframe)
        try:
            candles = self.market_data_service.get_candles(normalized_symbol, normalized_timeframe, count=250)
            return self.analyze_order_blocks_from_candles(normalized_symbol, normalized_timeframe, candles)
        except Exception as exc:
            logger.warning("Order block analysis unavailable for %s: %s", normalized_symbol, exc)
            return self.order_block_context_builder.build_order_block_context(
                normalized_symbol,
                normalized_timeframe,
                [],
            )
        finally:
            self.market_data_service.close()

    def analyze_order_blocks_from_candles(
        self,
        symbol: str,
        timeframe: str,
        candles: list[Any] | None,
    ) -> OrderBlockContext:
        normalized_symbol = validate_symbol_name(symbol)
        normalized_timeframe = validate_timeframe(timeframe)
        institutional_context = self.context_builder.build_context(normalized_symbol, normalized_timeframe, candles)
        fvg_context = self.fvg_context_builder.build_fvg_context(normalized_symbol, normalized_timeframe, candles)
        sweep_context = self.sweep_context_builder.build_sweep_context(
            normalized_symbol,
            normalized_timeframe,
            candles,
            institutional_context.liquidity_pools,
        )
        return self.order_block_context_builder.build_order_block_context(
            normalized_symbol,
            normalized_timeframe,
            candles,
            fvg_context=fvg_context,
            sweep_context=sweep_context,
            structure_bias=institutional_context.structure_bias,
        )

    def analyze_order_block_confluence(self, symbol: str, timeframe: str = "M15") -> dict[str, Any]:
        normalized_symbol = validate_symbol_name(symbol)
        normalized_timeframe = validate_timeframe(timeframe)
        try:
            candles = self.market_data_service.get_candles(normalized_symbol, normalized_timeframe, count=250)
        except Exception as exc:
            logger.warning("Order block confluence analysis unavailable for %s: %s", normalized_symbol, exc)
            candles = []
        finally:
            self.market_data_service.close()
        institutional_context = self.context_builder.build_context(normalized_symbol, normalized_timeframe, candles)
        fvg_context = self.fvg_context_builder.build_fvg_context(normalized_symbol, normalized_timeframe, candles)
        sweep_context = self.sweep_context_builder.build_sweep_context(
            normalized_symbol,
            normalized_timeframe,
            candles,
            institutional_context.liquidity_pools,
        )
        order_block_context = self.order_block_context_builder.build_order_block_context(
            normalized_symbol,
            normalized_timeframe,
            candles,
            fvg_context=fvg_context,
            sweep_context=sweep_context,
            structure_bias=institutional_context.structure_bias,
        )
        return {
            "symbol": normalized_symbol,
            "timeframe": normalized_timeframe,
            "order_blocks": order_block_context,
            "fair_value_gaps": fvg_context,
            "liquidity_sweeps": sweep_context,
            "structure_bias": institutional_context.structure_bias,
            "simulation_only": True,
            "live_execution_enabled": False,
        }

    def analyze_breaker_blocks(self, symbol: str, timeframe: str = "M15") -> BreakerBlockContext:
        normalized_symbol = validate_symbol_name(symbol)
        normalized_timeframe = validate_timeframe(timeframe)
        try:
            candles = self.market_data_service.get_candles(normalized_symbol, normalized_timeframe, count=250)
            return self.analyze_breaker_blocks_from_candles(normalized_symbol, normalized_timeframe, candles)
        except Exception as exc:
            logger.warning("Breaker block analysis unavailable for %s: %s", normalized_symbol, exc)
            return self.breaker_block_context_builder.build_breaker_context(
                normalized_symbol,
                normalized_timeframe,
                [],
            )
        finally:
            self.market_data_service.close()

    def analyze_breaker_blocks_from_candles(
        self,
        symbol: str,
        timeframe: str,
        candles: list[Any] | None,
    ) -> BreakerBlockContext:
        normalized_symbol = validate_symbol_name(symbol)
        normalized_timeframe = validate_timeframe(timeframe)
        institutional_context = self.context_builder.build_context(normalized_symbol, normalized_timeframe, candles)
        fvg_context = self.fvg_context_builder.build_fvg_context(normalized_symbol, normalized_timeframe, candles)
        sweep_context = self.sweep_context_builder.build_sweep_context(
            normalized_symbol,
            normalized_timeframe,
            candles,
            institutional_context.liquidity_pools,
        )
        order_block_context = self.order_block_context_builder.build_order_block_context(
            normalized_symbol,
            normalized_timeframe,
            candles,
            fvg_context=fvg_context,
            sweep_context=sweep_context,
            structure_bias=institutional_context.structure_bias,
        )
        return self.breaker_block_context_builder.build_breaker_context(
            normalized_symbol,
            normalized_timeframe,
            candles,
            order_block_context=order_block_context,
            fvg_context=fvg_context,
            sweep_context=sweep_context,
            structure_bias=institutional_context.structure_bias,
        )

    def analyze_breaker_confluence(self, symbol: str, timeframe: str = "M15") -> dict[str, Any]:
        normalized_symbol = validate_symbol_name(symbol)
        normalized_timeframe = validate_timeframe(timeframe)
        try:
            candles = self.market_data_service.get_candles(normalized_symbol, normalized_timeframe, count=250)
        except Exception as exc:
            logger.warning("Breaker confluence analysis unavailable for %s: %s", normalized_symbol, exc)
            candles = []
        finally:
            self.market_data_service.close()
        institutional_context = self.context_builder.build_context(normalized_symbol, normalized_timeframe, candles)
        fvg_context = self.fvg_context_builder.build_fvg_context(normalized_symbol, normalized_timeframe, candles)
        sweep_context = self.sweep_context_builder.build_sweep_context(
            normalized_symbol,
            normalized_timeframe,
            candles,
            institutional_context.liquidity_pools,
        )
        order_block_context = self.order_block_context_builder.build_order_block_context(
            normalized_symbol,
            normalized_timeframe,
            candles,
            fvg_context=fvg_context,
            sweep_context=sweep_context,
            structure_bias=institutional_context.structure_bias,
        )
        breaker_context = self.breaker_block_context_builder.build_breaker_context(
            normalized_symbol,
            normalized_timeframe,
            candles,
            order_block_context=order_block_context,
            fvg_context=fvg_context,
            sweep_context=sweep_context,
            structure_bias=institutional_context.structure_bias,
        )
        return {
            "symbol": normalized_symbol,
            "timeframe": normalized_timeframe,
            "breaker_blocks": breaker_context,
            "order_blocks": order_block_context,
            "fair_value_gaps": fvg_context,
            "liquidity_sweeps": sweep_context,
            "structure_bias": institutional_context.structure_bias,
            "simulation_only": True,
            "live_execution_enabled": False,
        }

    def analyze_structure_shift(self, symbol: str, timeframe: str = "M15") -> StructureShiftContext:
        normalized_symbol = validate_symbol_name(symbol)
        normalized_timeframe = validate_timeframe(timeframe)
        try:
            candles = self.market_data_service.get_candles(normalized_symbol, normalized_timeframe, count=250)
            return self.analyze_structure_shift_from_candles(normalized_symbol, normalized_timeframe, candles)
        except Exception as exc:
            logger.warning("Structure shift analysis unavailable for %s: %s", normalized_symbol, exc)
            return self.structure_shift_context_builder.build_structure_shift_context(
                normalized_symbol,
                normalized_timeframe,
                [],
            )
        finally:
            self.market_data_service.close()

    def analyze_structure_shift_from_candles(
        self,
        symbol: str,
        timeframe: str,
        candles: list[Any] | None,
    ) -> StructureShiftContext:
        normalized_symbol = validate_symbol_name(symbol)
        normalized_timeframe = validate_timeframe(timeframe)
        institutional_context = self.context_builder.build_context(normalized_symbol, normalized_timeframe, candles)
        fvg_context = self.fvg_context_builder.build_fvg_context(normalized_symbol, normalized_timeframe, candles)
        sweep_context = self.sweep_context_builder.build_sweep_context(
            normalized_symbol,
            normalized_timeframe,
            candles,
            institutional_context.liquidity_pools,
        )
        order_block_context = self.order_block_context_builder.build_order_block_context(
            normalized_symbol,
            normalized_timeframe,
            candles,
            fvg_context=fvg_context,
            sweep_context=sweep_context,
            structure_bias=institutional_context.structure_bias,
        )
        breaker_context = self.breaker_block_context_builder.build_breaker_context(
            normalized_symbol,
            normalized_timeframe,
            candles,
            order_block_context=order_block_context,
            fvg_context=fvg_context,
            sweep_context=sweep_context,
            structure_bias=institutional_context.structure_bias,
        )
        return self.structure_shift_context_builder.build_structure_shift_context(
            normalized_symbol,
            normalized_timeframe,
            candles,
            swings=institutional_context.swings,
            sweep_context=sweep_context,
            fvg_context=fvg_context,
            ob_context=order_block_context,
            breaker_context=breaker_context,
            structure_bias=institutional_context.structure_bias,
        )

    def analyze_structure_shift_confluence(self, symbol: str, timeframe: str = "M15") -> dict[str, Any]:
        normalized_symbol = validate_symbol_name(symbol)
        normalized_timeframe = validate_timeframe(timeframe)
        try:
            candles = self.market_data_service.get_candles(normalized_symbol, normalized_timeframe, count=250)
        except Exception as exc:
            logger.warning("Structure shift confluence unavailable for %s: %s", normalized_symbol, exc)
            candles = []
        finally:
            self.market_data_service.close()
        institutional_context = self.context_builder.build_context(normalized_symbol, normalized_timeframe, candles)
        fvg_context = self.fvg_context_builder.build_fvg_context(normalized_symbol, normalized_timeframe, candles)
        sweep_context = self.sweep_context_builder.build_sweep_context(
            normalized_symbol, normalized_timeframe, candles, institutional_context.liquidity_pools
        )
        order_block_context = self.order_block_context_builder.build_order_block_context(
            normalized_symbol, normalized_timeframe, candles, fvg_context, sweep_context, institutional_context.structure_bias
        )
        breaker_context = self.breaker_block_context_builder.build_breaker_context(
            normalized_symbol, normalized_timeframe, candles, order_block_context, fvg_context, sweep_context, institutional_context.structure_bias
        )
        structure_shift_context = self.structure_shift_context_builder.build_structure_shift_context(
            normalized_symbol,
            normalized_timeframe,
            candles,
            institutional_context.swings,
            sweep_context,
            fvg_context,
            order_block_context,
            breaker_context,
            institutional_context.structure_bias,
        )
        return {
            "symbol": normalized_symbol,
            "timeframe": normalized_timeframe,
            "structure_shift": structure_shift_context,
            "liquidity_sweeps": sweep_context,
            "fair_value_gaps": fvg_context,
            "order_blocks": order_block_context,
            "breaker_blocks": breaker_context,
            "structure_bias": institutional_context.structure_bias,
            "simulation_only": True,
            "live_execution_enabled": False,
        }

    def analyze_confluence(self, symbol: str, timeframe: str = "M15") -> ConfluenceContext:
        normalized_symbol = validate_symbol_name(symbol)
        normalized_timeframe = validate_timeframe(timeframe)
        try:
            candles = self.market_data_service.get_candles(normalized_symbol, normalized_timeframe, count=250)
            return self.analyze_confluence_from_candles(normalized_symbol, normalized_timeframe, candles)
        except Exception as exc:
            logger.warning("Institutional confluence analysis unavailable for %s: %s", normalized_symbol, exc)
            return self.confluence_context_builder.build_confluence_context(
                normalized_symbol,
                normalized_timeframe,
                [],
            )
        finally:
            self.market_data_service.close()

    def analyze_confluence_from_candles(
        self,
        symbol: str,
        timeframe: str,
        candles: list[Any] | None,
    ) -> ConfluenceContext:
        normalized_symbol = validate_symbol_name(symbol)
        normalized_timeframe = validate_timeframe(timeframe)
        return self.confluence_context_builder.build_confluence_context(
            normalized_symbol,
            normalized_timeframe,
            candles,
        )

    def analyze_multi_timeframe_alignment(self, symbol: str) -> MultiTimeframeAlignment:
        normalized_symbol = validate_symbol_name(symbol)
        return self.multi_timeframe_alignment_engine.analyze_alignment(normalized_symbol)

    def analyze_session_intelligence(self, symbol: str, timeframe: str = "M15") -> SessionIntelligenceContext:
        normalized_symbol = validate_symbol_name(symbol)
        normalized_timeframe = validate_timeframe(timeframe)
        try:
            candles = self.market_data_service.get_candles(normalized_symbol, normalized_timeframe, count=250)
            alignment = self.analyze_multi_timeframe_alignment(normalized_symbol)
            return self.analyze_session_intelligence_from_candles(
                normalized_symbol,
                normalized_timeframe,
                candles,
                alignment_context=alignment,
                news_status=self._safe_news_status(normalized_symbol),
            )
        except Exception as exc:
            logger.warning("Session intelligence unavailable for %s: %s", normalized_symbol, exc)
            return self.session_context_builder.build_session_context(
                normalized_symbol,
                normalized_timeframe,
                [],
            )
        finally:
            self.market_data_service.close()

    def analyze_session_intelligence_from_candles(
        self,
        symbol: str,
        timeframe: str,
        candles: list[Any] | None,
        alignment_context: MultiTimeframeAlignment | None = None,
        news_status: Any = None,
    ) -> SessionIntelligenceContext:
        normalized_symbol = validate_symbol_name(symbol)
        normalized_timeframe = validate_timeframe(timeframe)
        institutional_context = self.context_builder.build_context(normalized_symbol, normalized_timeframe, candles)
        sweep_context = self.sweep_context_builder.build_sweep_context(
            normalized_symbol,
            normalized_timeframe,
            candles,
            institutional_context.liquidity_pools,
        )
        confluence_context = self.confluence_context_builder.build_confluence_context(
            normalized_symbol,
            normalized_timeframe,
            candles,
        )
        return self.session_context_builder.build_session_context(
            normalized_symbol,
            normalized_timeframe,
            candles,
            sweep_context=sweep_context,
            news_status=news_status,
            confluence_context=confluence_context,
            alignment_context=alignment_context,
        )

    def _safe_news_status(self, symbol: str) -> Any:
        try:
            return self.news_filter_service.get_news_risk_status(symbol)
        except Exception as exc:
            logger.warning("News risk unavailable for session intelligence on %s: %s", symbol, exc)
            return None

    def analyze_entry_models(self, symbol: str, timeframe: str = "M15") -> EntryModelContext:
        normalized_symbol = validate_symbol_name(symbol)
        normalized_timeframe = validate_timeframe(timeframe)
        try:
            candles = self.market_data_service.get_candles(normalized_symbol, normalized_timeframe, count=250)
            alignment = self.analyze_multi_timeframe_alignment(normalized_symbol)
            news_status = self._safe_news_status(normalized_symbol)
            session = self.analyze_session_intelligence_from_candles(
                normalized_symbol,
                normalized_timeframe,
                candles,
                alignment_context=alignment,
                news_status=news_status,
            )
            return self.analyze_entry_models_from_candles(
                normalized_symbol,
                normalized_timeframe,
                candles,
                alignment_context=alignment,
                session_context=session,
                news_status=news_status,
            )
        except Exception as exc:
            logger.warning("Institutional entry model analysis unavailable for %s: %s", normalized_symbol, exc)
            return self.entry_model_context_builder.build_entry_model_context(
                normalized_symbol,
                normalized_timeframe,
                [],
            )
        finally:
            self.market_data_service.close()

    def analyze_entry_models_from_candles(
        self,
        symbol: str,
        timeframe: str,
        candles: list[Any] | None,
        alignment_context: MultiTimeframeAlignment | None = None,
        session_context: SessionIntelligenceContext | None = None,
        news_status: Any = None,
    ) -> EntryModelContext:
        normalized_symbol = validate_symbol_name(symbol)
        normalized_timeframe = validate_timeframe(timeframe)
        confluence = self.confluence_context_builder.build_confluence_context(
            normalized_symbol,
            normalized_timeframe,
            candles,
        )
        return self.entry_model_context_builder.build_entry_model_context(
            normalized_symbol,
            normalized_timeframe,
            candles,
            confluence_context=confluence,
            alignment_context=alignment_context,
            session_context=session_context,
            news_status=news_status,
        )

    def analyze_setup_validation(self, symbol: str, timeframe: str = "M15") -> SetupValidationContext:
        normalized_symbol = validate_symbol_name(symbol)
        normalized_timeframe = validate_timeframe(timeframe)
        try:
            candles = self.market_data_service.get_candles(normalized_symbol, normalized_timeframe, count=250)
            alignment = self.analyze_multi_timeframe_alignment(normalized_symbol)
            news_status = self._safe_news_status(normalized_symbol)
            confluence = self.confluence_context_builder.build_confluence_context(
                normalized_symbol, normalized_timeframe, candles
            )
            session = self.analyze_session_intelligence_from_candles(
                normalized_symbol,
                normalized_timeframe,
                candles,
                alignment_context=alignment,
                news_status=news_status,
            )
            entries = self.entry_model_context_builder.build_entry_model_context(
                normalized_symbol,
                normalized_timeframe,
                candles,
                confluence_context=confluence,
                alignment_context=alignment,
                session_context=session,
                news_status=news_status,
            )
            return self.setup_validation_context_builder.build_validation_context(
                normalized_symbol,
                normalized_timeframe,
                candles,
                entry_model_context=entries,
                confluence_context=confluence,
                alignment_context=alignment,
                session_context=session,
                risk_context=self._safe_risk_status(),
                news_status=news_status,
            )
        except Exception as exc:
            logger.warning("Setup validation unavailable for %s: %s", normalized_symbol, exc)
            return self.setup_validation_context_builder.build_validation_context(
                normalized_symbol,
                normalized_timeframe,
                [],
                risk_context=self._safe_risk_status(),
            )
        finally:
            self.market_data_service.close()

    def analyze_setup_validation_from_candles(
        self,
        symbol: str,
        timeframe: str,
        candles: list[Any] | None,
        alignment_context: MultiTimeframeAlignment | None = None,
        session_context: SessionIntelligenceContext | None = None,
        news_status: Any = None,
    ) -> SetupValidationContext:
        normalized_symbol = validate_symbol_name(symbol)
        normalized_timeframe = validate_timeframe(timeframe)
        confluence = self.confluence_context_builder.build_confluence_context(
            normalized_symbol, normalized_timeframe, candles
        )
        entries = self.entry_model_context_builder.build_entry_model_context(
            normalized_symbol,
            normalized_timeframe,
            candles,
            confluence_context=confluence,
            alignment_context=alignment_context,
            session_context=session_context,
            news_status=news_status,
        )
        return self.setup_validation_context_builder.build_validation_context(
            normalized_symbol,
            normalized_timeframe,
            candles,
            entry_model_context=entries,
            confluence_context=confluence,
            alignment_context=alignment_context,
            session_context=session_context,
            risk_context=self._safe_risk_status(),
            news_status=news_status,
        )

    def _safe_risk_status(self) -> Any:
        try:
            return self.risk_service.get_risk_status()
        except Exception as exc:
            logger.warning("Risk status unavailable for setup validation: %s", exc)
            return {"overall_status": "BLOCKED"}

    def analyze_simulation_decision(self, symbol: str, timeframe: str = "M15") -> SimulationDecisionContext:
        normalized_symbol = validate_symbol_name(symbol)
        normalized_timeframe = validate_timeframe(timeframe)
        try:
            candles = self.market_data_service.get_candles(normalized_symbol, normalized_timeframe, count=250)
            alignment = self.analyze_multi_timeframe_alignment(normalized_symbol)
            news_status = self._safe_news_status(normalized_symbol)
            session = self.analyze_session_intelligence_from_candles(
                normalized_symbol,
                normalized_timeframe,
                candles,
                alignment_context=alignment,
                news_status=news_status,
            )
            validation = self.analyze_setup_validation_from_candles(
                normalized_symbol,
                normalized_timeframe,
                candles,
                alignment_context=alignment,
                session_context=session,
                news_status=news_status,
            )
            return self.simulation_decision_context_builder.build_simulation_decision_context(
                normalized_symbol,
                normalized_timeframe,
                candles,
                validation_context=validation,
                risk_status=self._safe_risk_status(),
                news_status=news_status,
                session_context=session,
            )
        except Exception as exc:
            logger.warning("Institutional simulation decision unavailable for %s: %s", normalized_symbol, exc)
            return self.simulation_decision_context_builder.build_simulation_decision_context(
                normalized_symbol,
                normalized_timeframe,
                [],
                risk_status={"overall_status": "BLOCKED"},
            )
        finally:
            self.market_data_service.close()

    def analyze_simulation_decision_from_candles(
        self,
        symbol: str,
        timeframe: str,
        candles: list[Any] | None,
        alignment_context: MultiTimeframeAlignment | None = None,
        session_context: SessionIntelligenceContext | None = None,
        news_status: Any = None,
    ) -> SimulationDecisionContext:
        normalized_symbol = validate_symbol_name(symbol)
        normalized_timeframe = validate_timeframe(timeframe)
        validation = self.analyze_setup_validation_from_candles(
            normalized_symbol,
            normalized_timeframe,
            candles,
            alignment_context=alignment_context,
            session_context=session_context,
            news_status=news_status,
        )
        return self.simulation_decision_context_builder.build_simulation_decision_context(
            normalized_symbol,
            normalized_timeframe,
            candles,
            validation_context=validation,
            risk_status=self._safe_risk_status(),
            news_status=news_status,
            session_context=session_context,
        )

    def analyze_paper_trade_lifecycle(self, symbol: str, timeframe: str = "M15") -> PaperTradeLifecycleContext:
        normalized_symbol = validate_symbol_name(symbol)
        normalized_timeframe = validate_timeframe(timeframe)
        try:
            candles = self.market_data_service.get_candles(normalized_symbol, normalized_timeframe, count=250)
            decision = self.analyze_simulation_decision_from_candles(
                normalized_symbol, normalized_timeframe, candles
            )
            return self.paper_trade_context_builder.build_paper_trade_context(
                normalized_symbol,
                normalized_timeframe,
                candles,
                decision_context=decision,
            )
        except Exception as exc:
            logger.warning("Institutional paper trade lifecycle unavailable for %s: %s", normalized_symbol, exc)
            decision = self.simulation_decision_context_builder.build_simulation_decision_context(
                normalized_symbol,
                normalized_timeframe,
                [],
                risk_status={"overall_status": "BLOCKED"},
            )
            return self.paper_trade_context_builder.build_paper_trade_context(
                normalized_symbol,
                normalized_timeframe,
                [],
                decision_context=decision,
            )
        finally:
            self.market_data_service.close()

    def analyze_paper_trade_lifecycle_from_candles(
        self,
        symbol: str,
        timeframe: str,
        candles: list[Any] | None,
        decision_context: SimulationDecisionContext | None = None,
    ) -> PaperTradeLifecycleContext:
        normalized_symbol = validate_symbol_name(symbol)
        normalized_timeframe = validate_timeframe(timeframe)
        decision = decision_context or self.analyze_simulation_decision_from_candles(
            normalized_symbol,
            normalized_timeframe,
            candles,
        )
        return self.paper_trade_context_builder.build_paper_trade_context(
            normalized_symbol,
            normalized_timeframe,
            candles,
            decision_context=decision,
        )

    def get_position_management(self, symbol: str, timeframe: str = "M15") -> InstitutionalPositionManagement:
        normalized_symbol = validate_symbol_name(symbol)
        normalized_timeframe = validate_timeframe(timeframe)
        try:
            candles = self.market_data_service.get_candles(normalized_symbol, normalized_timeframe, count=250)
            return self.get_position_management_from_candles(normalized_symbol, normalized_timeframe, candles)
        except Exception as exc:
            logger.warning("Institutional position management unavailable for %s: %s", normalized_symbol, exc)
            paper = PaperTradeLifecycleContext(
                symbol=normalized_symbol,
                timeframe=normalized_timeframe,
                lifecycle_status="BLOCKED",
                summary="Paper lifecycle unavailable; position management remains inactive.",
            )
            return self.position_management_context_builder.build_position_management_context(
                normalized_symbol,
                normalized_timeframe,
                [],
                paper_context=paper,
                risk_context={"overall_status": "BLOCKED"},
            )
        finally:
            self.market_data_service.close()

    def get_position_management_from_candles(
        self,
        symbol: str,
        timeframe: str,
        candles: list[Any] | None,
        paper_context: PaperTradeLifecycleContext | None = None,
        structure_context: StructureShiftContext | None = None,
        breaker_context: BreakerBlockContext | None = None,
        session_context: SessionIntelligenceContext | None = None,
        risk_context: Any = None,
    ) -> InstitutionalPositionManagement:
        normalized_symbol = validate_symbol_name(symbol)
        normalized_timeframe = validate_timeframe(timeframe)
        paper = paper_context or self.analyze_paper_trade_lifecycle_from_candles(
            normalized_symbol, normalized_timeframe, candles
        )
        structure = structure_context or self.analyze_structure_shift_from_candles(
            normalized_symbol, normalized_timeframe, candles
        )
        breaker = breaker_context or self.analyze_breaker_blocks_from_candles(
            normalized_symbol, normalized_timeframe, candles
        )
        session = session_context or self.analyze_session_intelligence_from_candles(
            normalized_symbol, normalized_timeframe, candles
        )
        return self.position_management_context_builder.build_position_management_context(
            normalized_symbol,
            normalized_timeframe,
            candles,
            paper_context=paper,
            structure_context=structure,
            breaker_context=breaker,
            session_context=session,
            risk_context=risk_context if risk_context is not None else self._safe_risk_status(),
        )

    def get_active_position_management(self, symbol: str, timeframe: str = "M15") -> list[ManagedPosition]:
        return self.get_position_management(symbol, timeframe).active_positions

    def get_structural_exit_signals(self, symbol: str, timeframe: str = "M15") -> list[StructuralExitSignal]:
        return self.get_position_management(symbol, timeframe).structural_exit_signals

    def get_emergency_exit_status(self, symbol: str, timeframe: str = "M15") -> EmergencyExitSignal:
        context = self.get_position_management(symbol, timeframe)
        return context.emergency_exit or EmergencyExitSignal(
            shutdown_reason="No emergency simulation shutdown condition detected."
        )

    def analyze_institutional_orchestration(
        self, symbol: str, timeframe: str = "M15"
    ) -> InstitutionalOrchestrationReport:
        normalized_symbol = validate_symbol_name(symbol)
        normalized_timeframe = validate_timeframe(timeframe)
        try:
            candles = self.market_data_service.get_candles(normalized_symbol, normalized_timeframe, count=250)
            return self.institutional_orchestrator.analyze_from_candles(
                normalized_symbol, normalized_timeframe, candles
            )
        except Exception as exc:
            logger.warning("Institutional orchestration unavailable for %s: %s", normalized_symbol, exc)
            report = self.institutional_orchestrator.analyze_from_candles(
                normalized_symbol, normalized_timeframe, []
            )
            return report.model_copy(
                update={"warnings": report.warnings + ["Market data unavailable; report generated in safe fallback mode."]}
            )
        finally:
            self.market_data_service.close()

    def analyze_institutional_orchestration_from_candles(
        self,
        symbol: str,
        timeframe: str,
        candles: list[Any] | None,
    ) -> InstitutionalOrchestrationReport:
        normalized_symbol = validate_symbol_name(symbol)
        normalized_timeframe = validate_timeframe(timeframe)
        return self.institutional_orchestrator.analyze_from_candles(
            normalized_symbol, normalized_timeframe, candles
        )

    def analyze_ai_reasoning(self, symbol: str, timeframe: str = "M15") -> InstitutionalReasoningReport:
        normalized_symbol = validate_symbol_name(symbol)
        normalized_timeframe = validate_timeframe(timeframe)
        orchestration = self.analyze_institutional_orchestration(normalized_symbol, normalized_timeframe)
        return self.institutional_reasoning_engine.generate_reasoning(orchestration)

    def analyze_ai_reasoning_from_candles(
        self,
        symbol: str,
        timeframe: str,
        candles: list[Any] | None,
    ) -> InstitutionalReasoningReport:
        normalized_symbol = validate_symbol_name(symbol)
        normalized_timeframe = validate_timeframe(timeframe)
        orchestration = self.analyze_institutional_orchestration_from_candles(
            normalized_symbol, normalized_timeframe, candles
        )
        return self.institutional_reasoning_engine.generate_reasoning(orchestration)

    def analyze_performance_analytics(
        self, symbol: str, timeframe: str = "M15"
    ) -> InstitutionalPerformanceAnalyticsContext:
        normalized_symbol = validate_symbol_name(symbol)
        normalized_timeframe = validate_timeframe(timeframe)
        try:
            current_report = self.analyze_institutional_orchestration(normalized_symbol, normalized_timeframe)
            return self.performance_analytics_context_builder.build_performance_context(
                normalized_symbol, normalized_timeframe, [current_report]
            )
        except Exception as exc:
            logger.warning("Institutional performance analytics unavailable for %s: %s", normalized_symbol, exc)
            return self.performance_analytics_context_builder.build_performance_context(
                normalized_symbol, normalized_timeframe
            )
