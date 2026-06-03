from backend.nifty50.nifty_fvg_service import NIFTYFVGService
from backend.nifty50.nifty_liquidity_service import NIFTYLiquidityService
from backend.nifty50.nifty_confidence_engine import NIFTYConfidenceEngine
from backend.nifty50.nifty_order_block_service import NIFTYOrderBlockService
from backend.nifty50.nifty_regime_detector import NIFTYRegimeDetector
from backend.nifty50.nifty_strategy_models import NIFTYStrategySnapshot
from backend.nifty50.nifty_structure_service import NIFTYStructureService
from backend.nifty50.nifty_market_data_service import NIFTYMarketDataService


class NIFTYStrategyService:
    def __init__(
        self,
        liquidity_service: NIFTYLiquidityService | None = None,
        structure_service: NIFTYStructureService | None = None,
        fvg_service: NIFTYFVGService | None = None,
        order_block_service: NIFTYOrderBlockService | None = None,
        market_data_service: NIFTYMarketDataService | None = None,
    ) -> None:
        self.market_data_service = market_data_service or NIFTYMarketDataService()
        self.liquidity_service = liquidity_service or NIFTYLiquidityService(self.market_data_service)
        self.structure_service = structure_service or NIFTYStructureService(self.market_data_service)
        self.fvg_service = fvg_service or NIFTYFVGService(self.market_data_service)
        self.order_block_service = order_block_service or NIFTYOrderBlockService(self.market_data_service)
        self.regime_detector = NIFTYRegimeDetector()
        self.confidence_engine = NIFTYConfidenceEngine()

    def get_status(self) -> dict:
        return {
            "status": "SMC_INTELLIGENCE_READY",
            "symbol": "NIFTY50",
            "strategy_ready": True,
            "market_data_ready": True,
            "execution_ready": False,
            "placeholder": True,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "warnings": [
                "NIFTY50 strategy foundation reads manual market data but does not run full SMC calculations yet.",
                "No NIFTY50 execution path is enabled.",
            ],
        }

    def get_snapshot(self) -> NIFTYStrategySnapshot:
        has_data = not self.market_data_service.get_health().placeholder
        candles = self.market_data_service.candle_store.get_recent(limit=200)
        liquidity = self.liquidity_service.get_snapshot()
        structure = self.structure_service.get_snapshot()
        fvg = self.fvg_service.get_snapshot()
        order_block = self.order_block_service.get_snapshot()
        regime = self.regime_detector.classify(candles)
        confidence = self.confidence_engine.score(liquidity, structure, fvg, order_block, regime)
        if structure.structure_bias in {"BULLISH", "BEARISH"}:
            strategy_bias = structure.structure_bias
        elif regime == "TRENDING_BULLISH":
            strategy_bias = "BULLISH"
        elif regime == "TRENDING_BEARISH":
            strategy_bias = "BEARISH"
        else:
            strategy_bias = "NEUTRAL"
        return NIFTYStrategySnapshot(
            liquidity_context=liquidity,
            structure_context=structure,
            fvg_context=fvg,
            order_block_context=order_block,
            regime=regime,
            confidence=confidence,
            strategy_bias=strategy_bias,
            placeholder=not has_data,
        )

    def analyze(self) -> NIFTYStrategySnapshot:
        return self.get_snapshot()
