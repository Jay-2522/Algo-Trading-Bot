from typing import Any

from backend.institutional_intelligence.institutional_context import InstitutionalContextBuilder
from backend.institutional_intelligence.smc_models import InstitutionalContext
from backend.institutional_intelligence.liquidity_sweep_models import SweepContext
from backend.institutional_intelligence.sweep_context_builder import SweepContextBuilder
from backend.market_data.market_data_service import MarketDataService
from backend.market_data.validators import validate_symbol_name, validate_timeframe
from backend.utils.logger import get_logger


logger = get_logger(__name__)


class SMCService:
    """Analysis service for market structure intelligence; never performs execution."""

    def __init__(
        self,
        market_data_service: MarketDataService | None = None,
        context_builder: InstitutionalContextBuilder | None = None,
        sweep_context_builder: SweepContextBuilder | None = None,
    ) -> None:
        self.market_data_service = market_data_service or MarketDataService()
        self.context_builder = context_builder or InstitutionalContextBuilder()
        self.sweep_context_builder = sweep_context_builder or SweepContextBuilder()

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
