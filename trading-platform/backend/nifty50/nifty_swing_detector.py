from backend.nifty50.nifty_market_data_models import NIFTYCandle


class NIFTYSwingDetector:
    def detect_swing_highs(self, candles: list[NIFTYCandle]) -> list[dict]:
        swings: list[dict] = []
        for index in range(1, len(candles) - 1):
            previous = candles[index - 1]
            current = candles[index]
            following = candles[index + 1]
            if current.high > previous.high and current.high > following.high:
                strength = round(current.high - max(previous.high, following.high), 2)
                swings.append({"price": current.high, "timestamp": current.timestamp.isoformat(), "strength": max(strength, 0.0)})
        return swings

    def detect_swing_lows(self, candles: list[NIFTYCandle]) -> list[dict]:
        swings: list[dict] = []
        for index in range(1, len(candles) - 1):
            previous = candles[index - 1]
            current = candles[index]
            following = candles[index + 1]
            if current.low < previous.low and current.low < following.low:
                strength = round(min(previous.low, following.low) - current.low, 2)
                swings.append({"price": current.low, "timestamp": current.timestamp.isoformat(), "strength": max(strength, 0.0)})
        return swings
