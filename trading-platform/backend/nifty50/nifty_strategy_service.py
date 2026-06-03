from backend.nifty50.nifty_fvg_service import NIFTYFVGService
from backend.nifty50.nifty_liquidity_service import NIFTYLiquidityService
from backend.nifty50.nifty_order_block_service import NIFTYOrderBlockService
from backend.nifty50.nifty_strategy_models import NIFTYStrategySnapshot
from backend.nifty50.nifty_structure_service import NIFTYStructureService


class NIFTYStrategyService:
    def __init__(
        self,
        liquidity_service: NIFTYLiquidityService | None = None,
        structure_service: NIFTYStructureService | None = None,
        fvg_service: NIFTYFVGService | None = None,
        order_block_service: NIFTYOrderBlockService | None = None,
    ) -> None:
        self.liquidity_service = liquidity_service or NIFTYLiquidityService()
        self.structure_service = structure_service or NIFTYStructureService()
        self.fvg_service = fvg_service or NIFTYFVGService()
        self.order_block_service = order_block_service or NIFTYOrderBlockService()

    def get_status(self) -> dict:
        return {
            "status": "STRATEGY_FOUNDATION_READY",
            "symbol": "NIFTY50",
            "strategy_ready": True,
            "market_data_required": True,
            "execution_ready": False,
            "placeholder": True,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
            "warnings": [
                "NIFTY50 strategy foundation is placeholder-only until market data integration exists.",
                "No NIFTY50 execution path is enabled.",
            ],
        }

    def get_snapshot(self) -> NIFTYStrategySnapshot:
        return NIFTYStrategySnapshot(
            liquidity_context=self.liquidity_service.get_snapshot(),
            structure_context=self.structure_service.get_snapshot(),
            fvg_context=self.fvg_service.get_snapshot(),
            order_block_context=self.order_block_service.get_snapshot(),
            regime="UNKNOWN",
            confidence=0.0,
            strategy_bias="NEUTRAL",
            placeholder=True,
        )

    def analyze(self) -> NIFTYStrategySnapshot:
        return self.get_snapshot()
