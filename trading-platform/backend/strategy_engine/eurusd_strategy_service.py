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
