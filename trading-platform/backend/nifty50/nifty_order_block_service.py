from backend.nifty50.nifty_strategy_models import NIFTYOrderBlockContext


class NIFTYOrderBlockService:
    def __init__(self, market_data_service=None) -> None:
        self.market_data_service = market_data_service

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
        if not self.market_data_service:
            return NIFTYOrderBlockContext()
        candles = self.market_data_service.candle_store.get_recent(limit=200)
        if len(candles) < 3:
            return NIFTYOrderBlockContext()
        bullish: list[dict] = []
        bearish: list[dict] = []
        for index in range(1, len(candles)):
            previous = candles[index - 1]
            current = candles[index]
            current_range = max(current.high - current.low, 0.01)
            previous_bearish = previous.close < previous.open
            previous_bullish = previous.close > previous.open
            bullish_displacement = current.close > current.open and current.close > previous.high and current_range > max(previous.high - previous.low, 0.01)
            bearish_displacement = current.close < current.open and current.close < previous.low and current_range > max(previous.high - previous.low, 0.01)
            if previous_bearish and bullish_displacement:
                bullish.append(
                    {
                        "direction": "BULLISH",
                        "upper_bound": previous.high,
                        "lower_bound": previous.low,
                        "timestamp": previous.timestamp.isoformat(),
                    }
                )
            if previous_bullish and bearish_displacement:
                bearish.append(
                    {
                        "direction": "BEARISH",
                        "upper_bound": previous.high,
                        "lower_bound": previous.low,
                        "timestamp": previous.timestamp.isoformat(),
                    }
                )
        active = bullish[-1] if bullish else bearish[-1] if bearish else None
        return NIFTYOrderBlockContext(
            bullish_order_blocks=bullish,
            bearish_order_blocks=bearish,
            active_order_block=active,
            confidence=60.0 if active else 0.0,
            placeholder=False,
        )

    def get_snapshot(self) -> NIFTYOrderBlockContext:
        return self.analyze_order_blocks()
