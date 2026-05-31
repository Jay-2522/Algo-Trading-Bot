from backend.strategy_engine.eurusd_strategy_engine import EURUSDStrategyEngine


class EURUSDStrategyService:
    """Small service facade for Phase 8 EURUSD analysis endpoints."""

    def __init__(self, engine: EURUSDStrategyEngine | None = None) -> None:
        self.engine = engine or EURUSDStrategyEngine()

    def analyze(self, candles: list | None = None):
        return self.engine.analyze(candles=candles)

    def session_context(self):
        return self.engine.build_session_context()

    def indicator_context(self, candles: list | None = None):
        return self.engine.build_indicator_context(candles=candles)

    def liquidity_context(self, candles: list | None = None):
        return self.engine.build_liquidity_context(candles=candles)

    def structure_context(self, candles: list | None = None):
        liquidity_context = self.engine.build_liquidity_context(candles=candles)
        return self.engine.build_structure_context(candles=candles, liquidity_context=liquidity_context)

    def fvg_context(self, candles: list | None = None):
        liquidity_context = self.engine.build_liquidity_context(candles=candles)
        structure_context = self.engine.build_structure_context(candles=candles, liquidity_context=liquidity_context)
        return self.engine.build_fvg_context(
            candles=candles,
            structure_context=structure_context,
            liquidity_context=liquidity_context,
        )

    def order_block_context(self, candles: list | None = None):
        liquidity_context = self.engine.build_liquidity_context(candles=candles)
        structure_context = self.engine.build_structure_context(candles=candles, liquidity_context=liquidity_context)
        fvg_context = self.engine.build_fvg_context(
            candles=candles,
            structure_context=structure_context,
            liquidity_context=liquidity_context,
        )
        return self.engine.build_order_block_context(
            candles=candles,
            structure_context=structure_context,
            liquidity_context=liquidity_context,
            fvg_context=fvg_context,
        )

    def regime_context(self, candles: list | None = None):
        session_context = self.engine.build_session_context()
        indicator_context = self.engine.build_indicator_context(candles=candles)
        return self.engine.build_regime_context(
            candles=candles,
            indicator_context=indicator_context,
            session_context=session_context,
        )

    def confluence_context(self, candles: list | None = None):
        signal = self.engine.analyze(candles=candles)
        return {
            "symbol": signal.symbol,
            "action": signal.action,
            "confluence_score": signal.confluence_score.model_dump(mode="json") if signal.confluence_score else None,
            "confidence": signal.confidence,
            "trade_quality": signal.trade_quality,
            "aligned_confirmations": signal.aligned_confirmations,
            "missing_confirmations": signal.missing_confirmations,
            "risk_mode": signal.confluence_score.risk_mode if signal.confluence_score else "NO_TRADE",
            "client_summary": signal.client_summary,
            "technical_summary": signal.technical_summary,
            "execution_allowed": signal.execution_allowed,
            "simulation_only": signal.metadata.get("simulation_only", True),
            "live_execution_enabled": signal.metadata.get("live_execution_enabled", False),
        }
