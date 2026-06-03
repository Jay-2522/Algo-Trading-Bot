from backend.nifty50.nifty_strategy_models import NIFTYFVGContext


class NIFTYFVGService:
    def get_status(self) -> dict:
        return {
            "status": "PLACEHOLDER_READY",
            "component": "NIFTY50_FVG",
            "placeholder": True,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def analyze_fvg(self) -> NIFTYFVGContext:
        return NIFTYFVGContext()

    def get_snapshot(self) -> NIFTYFVGContext:
        return self.analyze_fvg()
