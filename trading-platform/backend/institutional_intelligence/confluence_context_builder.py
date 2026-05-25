from typing import Any

from backend.institutional_intelligence.breaker_block_context_builder import BreakerBlockContextBuilder
from backend.institutional_intelligence.breaker_block_models import BreakerBlockContext
from backend.institutional_intelligence.confluence_models import ConfluenceContext
from backend.institutional_intelligence.confluence_scorer import InstitutionalConfluenceScorer
from backend.institutional_intelligence.fair_value_gap_models import FVGContext
from backend.institutional_intelligence.fvg_context_builder import FVGContextBuilder
from backend.institutional_intelligence.institutional_context import InstitutionalContextBuilder
from backend.institutional_intelligence.liquidity_sweep_models import SweepContext
from backend.institutional_intelligence.order_block_context_builder import OrderBlockContextBuilder
from backend.institutional_intelligence.order_block_models import OrderBlockContext
from backend.institutional_intelligence.smc_models import InstitutionalContext
from backend.institutional_intelligence.structure_shift_context_builder import StructureShiftContextBuilder
from backend.institutional_intelligence.structure_shift_models import StructureShiftContext
from backend.institutional_intelligence.sweep_context_builder import SweepContextBuilder
from backend.risk_engine.risk_service import RiskService, get_risk_service
from backend.strategy_engine.session_manager import SessionManager


class ConfluenceContextBuilder:
    """Assemble all institutional observations into one safe scoring context."""

    def __init__(
        self,
        institutional_builder: InstitutionalContextBuilder | None = None,
        sweep_builder: SweepContextBuilder | None = None,
        fvg_builder: FVGContextBuilder | None = None,
        order_block_builder: OrderBlockContextBuilder | None = None,
        breaker_builder: BreakerBlockContextBuilder | None = None,
        structure_shift_builder: StructureShiftContextBuilder | None = None,
        scorer: InstitutionalConfluenceScorer | None = None,
        session_manager: SessionManager | None = None,
        risk_service: RiskService | None = None,
    ) -> None:
        self.institutional_builder = institutional_builder or InstitutionalContextBuilder()
        self.sweep_builder = sweep_builder or SweepContextBuilder()
        self.fvg_builder = fvg_builder or FVGContextBuilder()
        self.order_block_builder = order_block_builder or OrderBlockContextBuilder()
        self.breaker_builder = breaker_builder or BreakerBlockContextBuilder()
        self.structure_shift_builder = structure_shift_builder or StructureShiftContextBuilder()
        self.scorer = scorer or InstitutionalConfluenceScorer()
        self.session_manager = session_manager or SessionManager()
        self.risk_service = risk_service or get_risk_service()

    def build_confluence_context(
        self,
        symbol: str,
        timeframe: str,
        candles: list[Any] | None,
    ) -> ConfluenceContext:
        normalized_symbol = symbol.strip().upper()
        normalized_timeframe = timeframe.strip().upper()
        source = candles or []
        institutional = self._institutional(normalized_symbol, normalized_timeframe, source)
        sweeps = self._sweeps(normalized_symbol, normalized_timeframe, source, institutional)
        fvgs = self._fvgs(normalized_symbol, normalized_timeframe, source)
        order_blocks = self._order_blocks(
            normalized_symbol, normalized_timeframe, source, fvgs, sweeps, institutional
        )
        breakers = self._breakers(
            normalized_symbol, normalized_timeframe, source, order_blocks, fvgs, sweeps, institutional
        )
        shifts = self._structure_shifts(
            normalized_symbol,
            normalized_timeframe,
            source,
            institutional,
            sweeps,
            fvgs,
            order_blocks,
            breakers,
        )
        score = self.scorer.score_confluence(
            normalized_symbol,
            normalized_timeframe,
            institutional_context=institutional,
            sweep_context=sweeps,
            fvg_context=fvgs,
            order_block_context=order_blocks,
            breaker_context=breakers,
            structure_shift_context=shifts,
            session_context=self._safe_session(),
            risk_status=self._safe_risk_status(),
        )
        return ConfluenceContext(
            symbol=normalized_symbol,
            timeframe=normalized_timeframe,
            institutional_context=institutional,
            sweep_context=sweeps,
            fvg_context=fvgs,
            order_block_context=order_blocks,
            breaker_context=breakers,
            structure_shift_context=shifts,
            confluence_score=score,
        )

    def _institutional(self, symbol: str, timeframe: str, candles: list[Any]) -> InstitutionalContext:
        try:
            return self.institutional_builder.build_context(symbol, timeframe, candles)
        except Exception:
            return InstitutionalContext(symbol=symbol, timeframe=timeframe)

    def _sweeps(
        self, symbol: str, timeframe: str, candles: list[Any], institutional: InstitutionalContext
    ) -> SweepContext:
        try:
            return self.sweep_builder.build_sweep_context(symbol, timeframe, candles, institutional.liquidity_pools)
        except Exception:
            return SweepContext(symbol=symbol, timeframe=timeframe)

    def _fvgs(self, symbol: str, timeframe: str, candles: list[Any]) -> FVGContext:
        try:
            return self.fvg_builder.build_fvg_context(symbol, timeframe, candles)
        except Exception:
            return FVGContext(symbol=symbol, timeframe=timeframe)

    def _order_blocks(
        self,
        symbol: str,
        timeframe: str,
        candles: list[Any],
        fvgs: FVGContext,
        sweeps: SweepContext,
        institutional: InstitutionalContext,
    ) -> OrderBlockContext:
        try:
            return self.order_block_builder.build_order_block_context(
                symbol, timeframe, candles, fvgs, sweeps, institutional.structure_bias
            )
        except Exception:
            return OrderBlockContext(symbol=symbol, timeframe=timeframe)

    def _breakers(
        self,
        symbol: str,
        timeframe: str,
        candles: list[Any],
        order_blocks: OrderBlockContext,
        fvgs: FVGContext,
        sweeps: SweepContext,
        institutional: InstitutionalContext,
    ) -> BreakerBlockContext:
        try:
            return self.breaker_builder.build_breaker_context(
                symbol, timeframe, candles, order_blocks, fvgs, sweeps, institutional.structure_bias
            )
        except Exception:
            return BreakerBlockContext(symbol=symbol, timeframe=timeframe)

    def _structure_shifts(
        self,
        symbol: str,
        timeframe: str,
        candles: list[Any],
        institutional: InstitutionalContext,
        sweeps: SweepContext,
        fvgs: FVGContext,
        order_blocks: OrderBlockContext,
        breakers: BreakerBlockContext,
    ) -> StructureShiftContext:
        try:
            return self.structure_shift_builder.build_structure_shift_context(
                symbol,
                timeframe,
                candles,
                institutional.swings,
                sweeps,
                fvgs,
                order_blocks,
                breakers,
                institutional.structure_bias,
            )
        except Exception:
            return StructureShiftContext(symbol=symbol, timeframe=timeframe)

    def _safe_session(self) -> dict:
        try:
            return self.session_manager.get_session_info()
        except Exception:
            return {}

    def _safe_risk_status(self) -> Any:
        try:
            return self.risk_service.get_risk_status()
        except Exception:
            return None
