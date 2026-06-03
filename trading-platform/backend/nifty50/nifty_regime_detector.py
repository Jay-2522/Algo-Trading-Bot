from backend.nifty50.nifty_market_data_models import NIFTYCandle


class NIFTYRegimeDetector:
    def classify(self, candles: list[NIFTYCandle]) -> str:
        if len(candles) < 4:
            return "UNKNOWN"
        first = candles[0].close
        latest = candles[-1].close
        high = max(candle.high for candle in candles)
        low = min(candle.low for candle in candles)
        movement = latest - first
        full_range = max(high - low, 0.01)
        directional_ratio = abs(movement) / full_range
        if directional_ratio < 0.25:
            return "RANGING"
        if movement > 0:
            return "TRENDING_BULLISH"
        if movement < 0:
            return "TRENDING_BEARISH"
        return "UNKNOWN"
