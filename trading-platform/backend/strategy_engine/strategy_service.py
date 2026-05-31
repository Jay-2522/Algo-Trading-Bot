from typing import Any, Dict

from backend.strategy_engine.eurusd_strategy_service import EURUSDStrategyService
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
        eurusd_service: EURUSDStrategyService | None = None,
        signal_store: StrategySignalStore | None = None,
        market_session_service: MarketSessionService | None = None,
    ) -> None:
        self.market_data_service = market_data_service or MarketDataService()
        self.trend_analyzer = trend_analyzer or TrendAnalyzer()
        self.liquidity_detector = liquidity_detector or LiquidityDetector()
        self.structure_analyzer = structure_analyzer or StructureAnalyzer()
        self.session_manager = session_manager or SessionManager()
        self.xauusd_engine = xauusd_engine or XAUUSDStrategyEngine()
        self.eurusd_service = eurusd_service or EURUSDStrategyService()
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
                "liquidity_level_builder": True,
                "liquidity_sweep_detection": True,
                "sweep_strength_scoring": True,
                "swing_point_detection": True,
                "bos_choch_detection": True,
                "structure_strength_scoring": True,
                "fair_value_gap_detection": True,
                "fvg_quality_scoring": True,
                "order_block_detection": True,
                "order_block_quality_scoring": True,
                "market_regime_detection": True,
                "regime_quality_scoring": True,
                "confluence_confidence_scoring": True,
                "client_signal_reasoning": True,
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

    def analyze_eurusd(self, candles: list | None = None):
        """Analyze EURUSD and store the read-only strategy signal."""

        signal = self.eurusd_service.analyze(candles=candles)
        return self.signal_store.store_signal(signal)

    def get_eurusd_session_context(self):
        """Return current Phase 8 EURUSD session context."""

        return self.eurusd_service.session_context()

    def get_eurusd_indicator_context(self, candles: list | None = None):
        """Return Phase 8 EURUSD indicator context."""

        return self.eurusd_service.indicator_context(candles=candles)

    def analyze_eurusd_liquidity(self, candles: list | None = None):
        """Return Phase 8 EURUSD liquidity context."""

        return self.eurusd_service.liquidity_context(candles=candles)

    def analyze_eurusd_structure(self, candles: list | None = None):
        """Return Phase 8 EURUSD BOS/CHOCH structure context."""

        return self.eurusd_service.structure_context(candles=candles)

    def analyze_xauusd_liquidity(self, candles: list | None = None):
        """Return XAUUSD liquidity sweep context without generating execution intent."""

        return self.xauusd_engine.liquidity_detector.detect(symbol="XAUUSD", candles=candles)

    def analyze_xauusd_structure(self, candles: list | None = None):
        """Return XAUUSD BOS/CHOCH structure context without generating execution intent."""

        liquidity_context = self.xauusd_engine.liquidity_detector.detect(symbol="XAUUSD", candles=candles)
        return self.xauusd_engine.smc_detector.detect(
            symbol="XAUUSD",
            candles=candles,
            liquidity_context=liquidity_context,
        )

    def analyze_xauusd_fvg(self, candles: list | None = None) -> Dict[str, Any]:
        """Return XAUUSD FVG context without generating execution intent."""

        structure_context = self.analyze_xauusd_structure(candles=candles)
        return {
            "symbol": "XAUUSD",
            "fair_value_gaps": [fvg.model_dump(mode="json") for fvg in structure_context.fair_value_gaps],
            "latest_fvg": structure_context.latest_fvg.model_dump(mode="json") if structure_context.latest_fvg else None,
            "active_fvg_detected": structure_context.active_fvg_detected,
            "fvg_direction": structure_context.fvg_direction,
            "fvg_quality": structure_context.fvg_quality,
            "fvg_confidence": structure_context.fvg_confidence,
            "fvg_alignment_reason": structure_context.fvg_alignment_reason,
            "warnings": structure_context.warnings,
        }

    def analyze_xauusd_order_block(self, candles: list | None = None) -> Dict[str, Any]:
        """Return XAUUSD order block context without generating execution intent."""

        structure_context = self.analyze_xauusd_structure(candles=candles)
        return {
            "symbol": "XAUUSD",
            "order_blocks": [order_block.model_dump(mode="json") for order_block in structure_context.order_blocks],
            "latest_order_block": (
                structure_context.latest_order_block.model_dump(mode="json")
                if structure_context.latest_order_block
                else None
            ),
            "active_order_block_detected": structure_context.active_order_block_detected,
            "order_block_direction": structure_context.order_block_direction,
            "order_block_quality": structure_context.order_block_quality,
            "order_block_confidence": structure_context.order_block_confidence,
            "order_block_alignment_reason": structure_context.order_block_alignment_reason,
            "warnings": structure_context.warnings,
        }

    def analyze_xauusd_regime(self, candles: list | None = None) -> Dict[str, Any]:
        """Return XAUUSD market regime context without generating execution intent."""

        session_context = self.xauusd_engine.session_service.get_session_context()
        indicator_context = self.xauusd_engine.indicator_builder.build_context("XAUUSD", "H1", candles)
        regime_context = self.xauusd_engine.regime_detector.detect(
            symbol="XAUUSD",
            candles=candles,
            indicator_context=indicator_context,
            session_context=session_context,
        )
        return regime_context.model_dump(mode="json")

    def analyze_xauusd_confluence(self, candles: list | None = None) -> Dict[str, Any]:
        """Return final XAUUSD confluence scoring without generating execution intent."""

        signal = self.xauusd_engine.analyze(symbol="XAUUSD", candles=candles)
        return {
            "symbol": signal.symbol,
            "action": signal.action,
            "confluence_breakdown": signal.confluence_score.model_dump(mode="json"),
            "confidence": signal.confidence,
            "trade_quality": signal.trade_quality,
            "aligned_confirmations": signal.aligned_confirmations,
            "missing_confirmations": signal.missing_confirmations,
            "risk_mode": signal.confluence_score.risk_mode,
            "client_summary": signal.client_summary,
            "technical_summary": signal.technical_summary,
            "execution_allowed": signal.execution_allowed,
        }

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
