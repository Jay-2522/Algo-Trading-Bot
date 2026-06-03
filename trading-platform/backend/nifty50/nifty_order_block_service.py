from backend.nifty50.nifty_strategy_models import NIFTYOrderBlockContext


class NIFTYOrderBlockService:
    def get_status(self) -> dict:
        return {
            "status": "PLACEHOLDER_READY",
            "component": "NIFTY50_ORDER_BLOCK",
            "placeholder": True,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def analyze_order_blocks(self) -> NIFTYOrderBlockContext:
        return NIFTYOrderBlockContext()

    def get_snapshot(self) -> NIFTYOrderBlockContext:
        return self.analyze_order_blocks()
