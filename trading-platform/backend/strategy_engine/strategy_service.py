from typing import Any, Dict

from backend.market_data.market_data_service import MarketDataService
from backend.strategy_engine.liquidity_detector import LiquidityDetector
from backend.strategy_engine.market_session_service import MarketSessionService
from backend.strategy_engine.session_manager import SessionManager
from backend.strategy_engine.signal_models import StrategySnapshot
from backend.strategy_engine.strategy_signal_store import StrategySignalStore, strategy_signal_store
from backend.strategy_engine.structure_analyzer import StructureAnalyzer
from backend.strategy_engine.trend_analyzer import TrendAnalyzer
from backend.strategy_engine.validators import validate_strategy_symbol, validate_strategy_timeframe
from backend.strategy_engine.xauusd_strategy_engine import XAUUSDStrategyEngine


class StrategyService:
    """Analysis-only strategy service for institutional market context."""

    def __init__(
        self,
        market_data_service: MarketDataService | None = None,
        trend_analyzer: TrendAnalyzer | None = None,
        liquidity_detector: LiquidityDetector | None = None,
        structure_analyzer: StructureAnalyzer | None = None,
        session_manager: SessionManager | None = None,
        xauusd_engine: XAUUSDStrategyEngine | None = None,
        signal_store: StrategySignalStore | None = None,
        market_session_service: MarketSessionService | None = None,
    ) -> None:
        self.market_data_service = market_data_service or MarketDataService()
        self.trend_analyzer = trend_analyzer or TrendAnalyzer()
        self.liquidity_detector = liquidity_detector or LiquidityDetector()
        self.structure_analyzer = structure_analyzer or StructureAnalyzer()
        self.session_manager = session_manager or SessionManager()
        self.xauusd_engine = xauusd_engine or XAUUSDStrategyEngine()
        self.signal_store = signal_store or strategy_signal_store
        self.market_session_service = market_session_service or MarketSessionService()

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

    def get_status(self) -> Dict[str, Any]:
        """Return Phase 6 strategy-engine safety and readiness status."""

        return {
            "status": "OPERATIONAL",
            "engine": "XAUUSD_STRATEGY_ENGINE_FOUNDATION",
            "mode": "ANALYSIS_ONLY",
            "symbol": "XAUUSD",
            "higher_timeframes": ["H1", "H4"],
            "session_focus": ["LONDON", "NEW_YORK", "OVERLAP"],
            "features": {
                "session_context": True,
                "indicator_context": True,
                "liquidity_sweep_foundation": True,
                "smc_structure_placeholders": True,
                "risk_safe_signal_output": True,
            },
            "execution_allowed": False,
            "simulation_only": True,
            "demo_execution": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def analyze_xauusd(self, candles: list | None = None):
        """Analyze XAUUSD and store the read-only strategy signal."""

        signal = self.xauusd_engine.analyze(symbol="XAUUSD", candles=candles)
        return self.signal_store.store_signal(signal)

    def list_signals(self, limit: int = 100):
        """Return stored analysis signals."""

        return self.signal_store.list_signals(limit)

    def get_signal(self, signal_id: str):
        """Return one stored analysis signal by id."""

        return self.signal_store.get_signal(signal_id)

    def get_session_context(self):
        """Return current Phase 6 XAUUSD session context."""

        return self.market_session_service.get_session_context()

    def close(self) -> None:
        """Close owned market data resources."""

        self.market_data_service.close()
