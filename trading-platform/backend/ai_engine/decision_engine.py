from typing import Any

from backend.ai_engine.ai_models import MarketRegime, SignalScore, TradeDecision
from backend.ai_engine.confidence_engine import ConfidenceEngine
from backend.ai_engine.regime_classifier import RegimeClassifier
from backend.ai_engine.signal_scorer import SignalScorer
from backend.ai_engine.volatility_analyzer import VolatilityAnalyzer
from backend.broker_integrations.mt5.mt5_connection_manager import MT5ConnectionManager
from backend.broker_integrations.mt5.mt5_symbol_service import MT5SymbolService
from backend.risk_engine.risk_service import RiskService, get_risk_service
from backend.strategy_engine.liquidity_detector import LiquidityDetector
from backend.strategy_engine.session_manager import SessionManager
from backend.strategy_engine.structure_analyzer import StructureAnalyzer
from backend.strategy_engine.trend_analyzer import TrendAnalyzer


class DecisionEngine:
    """Generate advisory decisions only; it has no execution dependency."""

    def __init__(
        self,
        risk_service: RiskService | None = None,
        mt5_connection_manager: MT5ConnectionManager | None = None,
    ) -> None:
        self.risk_service = risk_service or get_risk_service()
        self.session_manager = SessionManager()
        self.trend_analyzer = TrendAnalyzer()
        self.liquidity_detector = LiquidityDetector()
        self.structure_analyzer = StructureAnalyzer()
        self.volatility_analyzer = VolatilityAnalyzer()
        self.signal_scorer = SignalScorer()
        self.confidence_engine = ConfidenceEngine()
        self.regime_classifier = RegimeClassifier()
        self.mt5_connection_manager = mt5_connection_manager or MT5ConnectionManager()
        self.symbol_service = MT5SymbolService(self.mt5_connection_manager)

    def evaluate_setup(
        self,
        symbol: str,
        strategy_context: dict[str, Any] | None = None,
        spread_quality: float | None = None,
    ) -> dict[str, Any]:
        """Evaluate a setup using safe context when market feeds are not connected."""

        normalized_symbol = symbol.strip().upper() if symbol else ""
        if not normalized_symbol:
            raise ValueError("Symbol cannot be empty.")

        context = strategy_context or self._foundation_context()
        session_info = context.get("session_info") or self.session_manager.get_session_info()
        risk_status = self.risk_service.get_risk_status().model_dump(mode="json")
        volatility = self.volatility_analyzer.evaluate_volatility(normalized_symbol)
        assessed_spread_quality = (
            spread_quality
            if spread_quality is not None
            else self._read_spread_quality(normalized_symbol)
        )
        signal_score = self.signal_scorer.score_trade_setup(
            context["trend_analysis"],
            context["liquidity_analysis"],
            context["structure_analysis"],
            session_info,
            assessed_spread_quality,
            risk_status,
            volatility["quality_score"],
        )
        trend_strength = signal_score.trend_score
        regime = self.regime_classifier.classify_market_regime(
            trend_strength=trend_strength,
            volatility=volatility["volatility_level"],
            spread=100 - assessed_spread_quality,
            liquidity=signal_score.liquidity_score,
            session_name=str(session_info.get("current_session", "Closed")),
        )
        confidence = self.confidence_engine.calculate_confidence(signal_score)
        decision = self._make_decision(
            normalized_symbol,
            context["trend_analysis"].get("trend", "ranging"),
            confidence,
            risk_status,
            regime,
            signal_score,
        )
        return {
            "decision": decision,
            "signal_score": signal_score,
            "regime": regime,
            "context": context,
        }

    def generate_trade_decision(
        self,
        symbol: str,
        strategy_context: dict[str, Any] | None = None,
    ) -> TradeDecision:
        return self.evaluate_setup(symbol, strategy_context)["decision"]

    def _make_decision(
        self,
        symbol: str,
        trend: str,
        confidence: float,
        risk_status: dict[str, Any],
        regime: MarketRegime,
        signal_score: SignalScore,
    ) -> TradeDecision:
        if risk_status.get("overall_status") != "OPERATIONAL":
            return TradeDecision(
                symbol=symbol,
                action="AVOID",
                confidence=confidence,
                approved=False,
                rejection_reason="Risk controls do not permit advisory approval.",
                regime=regime,
                signal_score=signal_score,
            )
        if regime.regime in {"VOLATILE", "LOW_LIQUIDITY", "NEWS_RISK"}:
            return TradeDecision(
                symbol=symbol,
                action="AVOID",
                confidence=confidence,
                approved=False,
                rejection_reason=f"Market regime is {regime.regime}.",
                regime=regime,
                signal_score=signal_score,
            )
        if confidence >= 75 and trend in {"bullish", "bearish"}:
            return TradeDecision(
                symbol=symbol,
                action="BUY" if trend == "bullish" else "SELL",
                confidence=confidence,
                approved=True,
                rejection_reason=None,
                regime=regime,
                signal_score=signal_score,
            )
        if confidence >= 50:
            action = "WAIT"
            reason = "Setup lacks sufficient directional alignment."
        else:
            action = "AVOID"
            reason = "Setup confidence is below quality threshold."
        return TradeDecision(
            symbol=symbol,
            action=action,
            confidence=confidence,
            approved=False,
            rejection_reason=reason,
            regime=regime,
            signal_score=signal_score,
        )

    def _foundation_context(self) -> dict[str, Any]:
        return {
            "trend_analysis": self.trend_analyzer.determine_trend([]),
            "liquidity_analysis": self.liquidity_detector.detect_liquidity_zones([]),
            "structure_analysis": self.structure_analyzer.analyze_market_structure([]),
            "session_info": self.session_manager.get_session_info(),
        }

    def _read_spread_quality(self, symbol: str) -> float:
        """Read spread only from an already initialized MT5 data connection."""

        symbol_info = self.symbol_service.get_symbol_info(symbol)
        if symbol_info.spread is None:
            return 80.0
        max_reference_spread = self.risk_service.config.max_allowed_spread
        utilization = min(float(symbol_info.spread) / max_reference_spread, 1.0)
        return round(100 * (1 - utilization), 2)
