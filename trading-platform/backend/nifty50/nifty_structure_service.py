from backend.nifty50.nifty_bos_detector import NIFTYBOSDetector
from backend.nifty50.nifty_choch_detector import NIFTYCHOCHDetector
from backend.nifty50.nifty_swing_detector import NIFTYSwingDetector
from backend.nifty50.nifty_strategy_models import NIFTYStructureContext


class NIFTYStructureService:
    def __init__(self, market_data_service=None) -> None:
        self.market_data_service = market_data_service
        self.swing_detector = NIFTYSwingDetector()
        self.bos_detector = NIFTYBOSDetector()
        self.choch_detector = NIFTYCHOCHDetector()

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
        if not self.market_data_service:
            return NIFTYStructureContext()
        candles = self.market_data_service.candle_store.get_recent(limit=200)
        if len(candles) < 4:
            return NIFTYStructureContext()
        swing_highs = self.swing_detector.detect_swing_highs(candles)
        swing_lows = self.swing_detector.detect_swing_lows(candles)
        swings = {"swing_highs": swing_highs, "swing_lows": swing_lows}
        bos = self.bos_detector.detect_bos(candles, swings)
        choch = self.choch_detector.detect_choch(candles, swings)
        direction = bos["direction"] if bos["bos_detected"] else choch["direction"] if choch["choch_detected"] else "NEUTRAL"
        bias = "BULLISH" if direction == "BULLISH" else "BEARISH" if direction == "BEARISH" else "NEUTRAL"
        strength = max(float(bos.get("strength", 0.0)), float(choch.get("strength", 0.0)))
        return NIFTYStructureContext(
            swing_highs=swing_highs,
            swing_lows=swing_lows,
            bos_detected=bool(bos["bos_detected"]),
            choch_detected=bool(choch["choch_detected"]),
            bos_direction=str(bos["direction"]),
            choch_direction=str(choch["direction"]),
            bos_break_price=bos["break_price"],
            structure_bias=bias,
            structure_strength=strength,
            placeholder=False,
        )

    def get_snapshot(self) -> NIFTYStructureContext:
        return self.analyze_structure()
