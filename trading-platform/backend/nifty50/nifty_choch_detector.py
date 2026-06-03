from backend.nifty50.nifty_market_data_models import NIFTYCandle


class NIFTYCHOCHDetector:
    def detect_choch(self, candles: list[NIFTYCandle], swings: dict) -> dict:
        if len(candles) < 4:
            return {"choch_detected": False, "direction": "NONE", "strength": 0.0}
        first_close = candles[0].close
        latest = candles[-1]
        prior_bias = "BULLISH" if candles[-2].close > first_close else "BEARISH" if candles[-2].close < first_close else "NEUTRAL"
        swing_highs = swings.get("swing_highs", [])
        swing_lows = swings.get("swing_lows", [])
        last_high = swing_highs[-1]["price"] if swing_highs else None
        last_low = swing_lows[-1]["price"] if swing_lows else None
        if prior_bias == "BEARISH" and last_high is not None and latest.close > last_high:
            return {"choch_detected": True, "direction": "BULLISH", "strength": round(latest.close - last_high, 2)}
        if prior_bias == "BULLISH" and last_low is not None and latest.close < last_low:
            return {"choch_detected": True, "direction": "BEARISH", "strength": round(last_low - latest.close, 2)}
        return {"choch_detected": False, "direction": "NONE", "strength": 0.0}
