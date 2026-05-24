from typing import Any, Dict

from backend.market_data.market_data_service import MarketDataService
from backend.strategy_engine.liquidity_detector import LiquidityDetector
from backend.strategy_engine.session_manager import SessionManager
from backend.strategy_engine.signal_models import StrategySnapshot
from backend.strategy_engine.structure_analyzer import StructureAnalyzer
from backend.strategy_engine.trend_analyzer import TrendAnalyzer
from backend.strategy_engine.validators import validate_strategy_symbol, validate_strategy_timeframe


class StrategyService:
    """Analysis-only strategy service for institutional market context."""

    def __init__(
        self,
        market_data_service: MarketDataService | None = None,
        trend_analyzer: TrendAnalyzer | None = None,
        liquidity_detector: LiquidityDetector | None = None,
        structure_analyzer: StructureAnalyzer | None = None,
        session_manager: SessionManager | None = None,
    ) -> None:
        self.market_data_service = market_data_service or MarketDataService()
        self.trend_analyzer = trend_analyzer or TrendAnalyzer()
        self.liquidity_detector = liquidity_detector or LiquidityDetector()
        self.structure_analyzer = structure_analyzer or StructureAnalyzer()
        self.session_manager = session_manager or SessionManager()

    def analyze_symbol(self, symbol: str, timeframe: str = "M15") -> Dict[str, Any]:
        """Analyze a symbol without creating executable trading instructions."""

        normalized_symbol = validate_strategy_symbol(symbol)
        normalized_timeframe = validate_strategy_timeframe(timeframe)
        candles = self.market_data_service.get_candles(normalized_symbol, normalized_timeframe, count=250)

        return {
            "symbol": normalized_symbol,
            "timeframe": normalized_timeframe,
            "trend_analysis": self.trend_analyzer.determine_trend(candles),
            "liquidity_analysis": self.liquidity_detector.detect_liquidity_zones(candles),
            "structure_analysis": self.structure_analyzer.analyze_market_structure(candles),
            "session_info": self.session_manager.get_session_info(),
            "status": "analysis_ready",
        }

    def get_strategy_snapshot(self, symbol: str, timeframe: str = "M15") -> StrategySnapshot:
        """Return a Pydantic snapshot for API and future engine integration."""

        analysis = self.analyze_symbol(symbol, timeframe)
        trend_confidence = float(analysis["trend_analysis"].get("confidence", 0.0))
        return StrategySnapshot(
            symbol=analysis["symbol"],
            timeframe=analysis["timeframe"],
            confidence=trend_confidence,
            trend_analysis=analysis["trend_analysis"],
            liquidity_analysis=analysis["liquidity_analysis"],
            structure_analysis=analysis["structure_analysis"],
            session_info=analysis["session_info"],
            metadata={"source": "strategy_engine_foundation"},
        )

    def close(self) -> None:
        """Close owned market data resources."""

        self.market_data_service.close()

