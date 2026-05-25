from typing import Any

from backend.institutional_intelligence.institutional_context import InstitutionalContextBuilder
from backend.institutional_intelligence.smc_models import InstitutionalContext
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
    ) -> None:
        self.market_data_service = market_data_service or MarketDataService()
        self.context_builder = context_builder or InstitutionalContextBuilder()

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
