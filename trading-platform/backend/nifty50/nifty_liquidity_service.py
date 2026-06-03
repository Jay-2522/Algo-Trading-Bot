from backend.nifty50.nifty_swing_detector import NIFTYSwingDetector
from backend.nifty50.nifty_strategy_models import NIFTYLiquidityContext


class NIFTYLiquidityService:
    def __init__(self, market_data_service=None) -> None:
        self.market_data_service = market_data_service
        self.swing_detector = NIFTYSwingDetector()

    def get_status(self) -> dict:
        return {
            "status": "PLACEHOLDER_READY",
            "component": "NIFTY50_LIQUIDITY",
            "market_data_required": True,
            "placeholder": True,
            "simulation_only": True,
            "live_execution_enabled": False,
            "broker_execution_enabled": False,
        }

    def analyze_liquidity(self) -> NIFTYLiquidityContext:
        if not self.market_data_service:
            return NIFTYLiquidityContext()
        candles = self.market_data_service.candle_store.get_recent(limit=200)
        if len(candles) < 4:
            return NIFTYLiquidityContext(placeholder=True)
        swing_highs = self.swing_detector.detect_swing_highs(candles[:-1])
        swing_lows = self.swing_detector.detect_swing_lows(candles[:-1])
        latest = candles[-1]
        previous_high = swing_highs[-1]["price"] if swing_highs else None
        previous_low = swing_lows[-1]["price"] if swing_lows else None
        sweep_detected = False
        sweep_direction = "NONE"
        if previous_high is not None and latest.high > previous_high and latest.close < previous_high:
            sweep_detected = True
            sweep_direction = "BUY_SIDE"
        elif previous_low is not None and latest.low < previous_low and latest.close > previous_low:
            sweep_detected = True
            sweep_direction = "SELL_SIDE"
        pools = []
        if previous_high is not None:
            pools.append({"type": "SWING_HIGH", "price": previous_high})
        if previous_low is not None:
            pools.append({"type": "SWING_LOW", "price": previous_low})
        return NIFTYLiquidityContext(
            previous_day_high=max(candle.high for candle in candles),
            previous_day_low=min(candle.low for candle in candles),
            weekly_high=max(candle.high for candle in candles),
            weekly_low=min(candle.low for candle in candles),
            liquidity_pools=pools,
            sweep_detected=sweep_detected,
            sweep_direction=sweep_direction,
            confidence=65.0 if sweep_detected else 20.0,
            placeholder=False,
        )

    def get_snapshot(self) -> NIFTYLiquidityContext:
        return self.analyze_liquidity()
