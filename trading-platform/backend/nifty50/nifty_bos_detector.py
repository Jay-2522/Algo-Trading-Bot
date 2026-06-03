from backend.nifty50.nifty_market_data_models import NIFTYCandle


class NIFTYBOSDetector:
    def detect_bos(self, candles: list[NIFTYCandle], swings: dict) -> dict:
        if not candles:
            return {"bos_detected": False, "direction": "NONE", "break_price": None, "strength": 0.0}
        latest = candles[-1]
        swing_highs = swings.get("swing_highs", [])
        swing_lows = swings.get("swing_lows", [])
        last_high = swing_highs[-1]["price"] if swing_highs else None
        last_low = swing_lows[-1]["price"] if swing_lows else None
        if last_high is not None and latest.close > last_high:
            return {
                "bos_detected": True,
                "direction": "BULLISH",
                "break_price": last_high,
                "strength": round(latest.close - last_high, 2),
            }
        if last_low is not None and latest.close < last_low:
            return {
                "bos_detected": True,
                "direction": "BEARISH",
                "break_price": last_low,
                "strength": round(last_low - latest.close, 2),
            }
        return {"bos_detected": False, "direction": "NONE", "break_price": None, "strength": 0.0}
