from backend.nifty50.nifty_strategy_models import NIFTYStructureContext


class NIFTYStructureService:
    def get_status(self) -> dict:
        return {
            "status": "PLACEHOLDER_READY",
            "component": "NIFTY50_STRUCTURE",
            "bos_detection_enabled": False,
            "choch_detection_enabled": False,
            "placeholder": True,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def analyze_structure(self) -> NIFTYStructureContext:
        return NIFTYStructureContext(bos_detected=False, choch_detected=False)

    def get_snapshot(self) -> NIFTYStructureContext:
        return self.analyze_structure()
